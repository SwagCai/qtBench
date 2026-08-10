"""Optional, provider-neutral, non-authoritative AI review for qtBench."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Protocol


MAX_ARTIFACT_BYTES = 128 * 1024
PROMPT_PATH = Path("docs/cheating/ai_judge_prompt.md")
TAXONOMY_PATH = Path("docs/cheating/taxonomy.md")
REGISTRY_PATH = Path("problems/registry.json")
REDACTION_MARKER = "[REDACTED_PROVIDER_CREDENTIAL]"

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "risk_level": {
            "type": "string",
            "enum": ["low", "elevated", "high", "indeterminate"],
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "taxonomy_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "title": {"type": "string"},
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical", "unknown"],
                    },
                    "evidence_lines": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                    },
                    "evidence_summary": {"type": "string"},
                    "analysis": {"type": "string"},
                    "recommended_action": {"type": "string"},
                },
                "required": [
                    "taxonomy_ids",
                    "title",
                    "risk_level",
                    "evidence_lines",
                    "evidence_summary",
                    "analysis",
                    "recommended_action",
                ],
            },
        },
        "limitations": {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "risk_level",
        "confidence",
        "summary",
        "findings",
        "limitations",
        "recommended_actions",
    ],
}


class JudgeError(RuntimeError):
    """A local configuration or input error."""


class JudgeRequestError(RuntimeError):
    """A provider request or response error."""


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    display_name: str
    credential_env_vars: tuple[str, ...]
    install_extra: str
    retention_control: str


PROVIDER_SPECS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        name="openai",
        display_name="OpenAI",
        credential_env_vars=("OPENAI_API_KEY",),
        install_extra="ai-judge-openai",
        retention_control="request_store_false",
    ),
    "anthropic": ProviderSpec(
        name="anthropic",
        display_name="Anthropic",
        credential_env_vars=("ANTHROPIC_API_KEY",),
        install_extra="ai-judge-anthropic",
        retention_control="provider_account_policy",
    ),
    "google": ProviderSpec(
        name="google",
        display_name="Google Gemini",
        credential_env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        install_extra="ai-judge-google",
        retention_control="provider_account_policy",
    ),
}


@dataclass(frozen=True)
class ProblemContext:
    id: int
    name: str
    title: str
    task_type: str
    evaluator_kind: str
    statement: str


@dataclass(frozen=True)
class Artifact:
    name: str
    text: str
    byte_count: int
    sha256: str


@dataclass(frozen=True)
class PromptBundle:
    instructions: str
    input_text: str
    hashes: Mapping[str, str]
    credential_redacted: bool
    safe_artifact_name: str


@dataclass(frozen=True)
class ProviderResponse:
    output_text: str
    response_id: str | None
    model: str | None


class ProviderAdapter(Protocol):
    """Provider extension point for one tool-free structured review request."""

    name: str

    def assess(
        self,
        *,
        model: str,
        max_output_tokens: int,
        prompt: PromptBundle,
    ) -> ProviderResponse: ...


class OpenAIProvider:
    name = "openai"

    def __init__(self, client: Any):
        self._client = client

    def assess(
        self,
        *,
        model: str,
        max_output_tokens: int,
        prompt: PromptBundle,
    ) -> ProviderResponse:
        response = self._client.responses.create(
            model=model,
            instructions=prompt.instructions,
            input=prompt.input_text,
            max_output_tokens=max_output_tokens,
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "qtbench_ai_judge_verdict",
                    "strict": True,
                    "schema": VERDICT_SCHEMA,
                }
            },
        )
        return ProviderResponse(
            output_text=getattr(response, "output_text", ""),
            response_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: Any):
        self._client = client

    def assess(
        self,
        *,
        model: str,
        max_output_tokens: int,
        prompt: PromptBundle,
    ) -> ProviderResponse:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_output_tokens,
            system=prompt.instructions,
            messages=[{"role": "user", "content": prompt.input_text}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": VERDICT_SCHEMA,
                }
            },
        )
        output_text = "".join(
            block.text
            for block in getattr(response, "content", ())
            if getattr(block, "type", None) == "text"
            and isinstance(getattr(block, "text", None), str)
        )
        return ProviderResponse(
            output_text=output_text,
            response_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
        )


class GoogleProvider:
    name = "google"

    def __init__(self, client: Any):
        self._client = client

    def assess(
        self,
        *,
        model: str,
        max_output_tokens: int,
        prompt: PromptBundle,
    ) -> ProviderResponse:
        response = self._client.models.generate_content(
            model=model,
            contents=prompt.input_text,
            config={
                "system_instruction": prompt.instructions,
                "max_output_tokens": max_output_tokens,
                "response_mime_type": "application/json",
                "response_json_schema": VERDICT_SCHEMA,
            },
        )
        return ProviderResponse(
            output_text=getattr(response, "text", ""),
            response_id=getattr(response, "response_id", None),
            model=getattr(response, "model_version", None),
        )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redaction_marker(credential: str) -> str:
    """Return a marker that cannot itself contain the selected credential."""

    if not credential:
        raise JudgeError("provider credential must not be empty")
    for marker in (REDACTION_MARKER, "<credential removed>", "*"):
        if credential not in marker:
            return marker
    raise AssertionError("unreachable redaction-marker collision")


def _repo_root(candidate: Path) -> Path:
    try:
        candidate = candidate.resolve()
    except (OSError, RuntimeError):
        raise JudgeError(f"could not resolve repository root: {candidate}") from None
    search = (candidate, *candidate.parents)
    for root in search:
        try:
            registry = (root / REGISTRY_PATH).resolve()
            taxonomy = (root / TAXONOMY_PATH).resolve()
        except (OSError, RuntimeError):
            continue
        if (
            registry.is_relative_to(root)
            and taxonomy.is_relative_to(root)
            and registry.is_file()
            and taxonomy.is_file()
        ):
            return root
    raise JudgeError(
        f"{candidate} is not inside a qtBench checkout; pass --repo-root"
    )


def _trusted_repo_path(root: Path, relative: str | Path) -> Path:
    try:
        path = (root / relative).resolve()
    except (OSError, RuntimeError):
        raise JudgeError(f"could not resolve repository path: {relative}") from None
    if not path.is_relative_to(root):
        raise JudgeError(f"repository path escapes checkout: {relative}")
    return path


def _strict_json_loads(document: str) -> Any:
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key {key!r}")
            result[key] = value
        return result

    def reject_nonstandard_constant(value: str):
        raise ValueError(f"non-standard JSON constant {value}")

    return json.loads(
        document,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonstandard_constant,
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise JudgeError(f"could not read repository data: {path}") from error
    if not isinstance(value, dict):
        raise JudgeError(f"repository data must be a JSON object: {path}")
    return value


def load_problem_context(repo_root: Path, selector: str) -> ProblemContext:
    root = _repo_root(repo_root)
    registry = _read_json_object(_trusted_repo_path(root, REGISTRY_PATH))
    entries = registry.get("problems")
    if not isinstance(entries, list):
        raise JudgeError("problem registry has no problem list")

    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    try:
        numeric_selector = (
            int(selector) if selector.isascii() and selector.isdigit() else None
        )
    except ValueError:
        raise JudgeError("numeric problem selector is too large") from None
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise JudgeError("problem registry contains a non-object entry")
        statement_value = raw_entry.get("problem_statement")
        if not isinstance(statement_value, str):
            raise JudgeError("problem registry entry has no problem statement")
        statement_path = _trusted_repo_path(root, statement_value)
        metadata = _read_json_object(
            _trusted_repo_path(
                root,
                statement_path.parent.relative_to(root) / "metadata.json",
            )
        )
        if (
            numeric_selector is not None
            and raw_entry.get("id") == numeric_selector
            or raw_entry.get("name") == selector
            or metadata.get("evaluator_kind") == selector
        ):
            matches.append((raw_entry, metadata))

    if not matches:
        raise JudgeError(f"unknown problem selector: {selector}")
    if len(matches) != 1:
        raise JudgeError(f"ambiguous problem selector: {selector}")

    entry, metadata = matches[0]
    statement_path = _trusted_repo_path(root, entry["problem_statement"])
    try:
        statement = statement_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise JudgeError(f"could not read problem statement: {statement_path}") from error

    required = {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "title": entry.get("title"),
        "task_type": entry.get("task_type"),
        "evaluator_kind": metadata.get("evaluator_kind"),
    }
    if type(required["id"]) is not int or any(
        not isinstance(value, str) or not value
        for key, value in required.items()
        if key != "id"
    ):
        raise JudgeError("selected problem has incomplete registry metadata")
    return ProblemContext(statement=statement, **required)


def read_artifact(path: Path, max_bytes: int = MAX_ARTIFACT_BYTES) -> Artifact:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise JudgeError("could not open artifact as a regular file") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise JudgeError("artifact must be a regular file")
        if opened.st_size > max_bytes:
            raise JudgeError(f"artifact exceeds the {max_bytes}-byte limit")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(descriptor)

    raw = b"".join(chunks)
    if len(raw) > max_bytes:
        raise JudgeError(f"artifact exceeds the {max_bytes}-byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise JudgeError("artifact must be UTF-8 text") from error
    return Artifact(
        name=path.name,
        text=text,
        byte_count=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def build_prompt(
    repo_root: Path,
    problem: ProblemContext,
    artifact: Artifact,
    credential: str,
) -> PromptBundle:
    if not credential:
        raise JudgeError("provider credential must not be empty")
    root = _repo_root(repo_root)
    try:
        template = _trusted_repo_path(root, PROMPT_PATH).read_text(encoding="utf-8")
        taxonomy = _trusted_repo_path(root, TAXONOMY_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise JudgeError("could not read the versioned AI judge prompt inputs") from error

    raw_instructions = (
        f"{template}\n\n"
        "# Trusted selected task description\n\n"
        f"{problem.statement}\n\n"
        "# Trusted qtBench cheating taxonomy\n\n"
        f"{taxonomy}"
    )
    redaction = _redaction_marker(credential)
    redacted_text = artifact.text.replace(credential, redaction)
    safe_artifact_name = artifact.name.replace(credential, redaction)
    numbered = "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(redacted_text.splitlines(), start=1)
    )
    input_text = (
        f"Review artifact {safe_artifact_name!r} for qtBench problem "
        f"{problem.id} ({problem.name}).\n\n"
        "<untrusted_submission>\n"
        f"{numbered}\n"
        "</untrusted_submission>"
    )
    if credential in raw_instructions:
        raise JudgeError(
            "provider credential appears in trusted AI-judge prompt text; "
            "refusing to alter or send the prompt"
        )
    if credential in input_text:
        raise JudgeError(
            "provider credential remains in the AI-judge prompt after artifact "
            "redaction; refusing to send the prompt"
        )
    hashes = {
        "template_sha256": _sha256(template),
        "taxonomy_sha256": _sha256(taxonomy),
        "problem_statement_sha256": _sha256(problem.statement),
        "instructions_sha256": _sha256(raw_instructions),
        "input_sha256": _sha256(input_text),
    }
    return PromptBundle(
        instructions=raw_instructions,
        input_text=input_text,
        hashes=hashes,
        credential_redacted=(
            redacted_text != artifact.text
            or safe_artifact_name != artifact.name
        ),
        safe_artifact_name=safe_artifact_name,
    )


def resolve_credential(
    provider: str,
    *,
    prompt_for_credential: bool,
    environ: Mapping[str, str] | None = None,
    prompt_fn: Callable[[str], str] = getpass.getpass,
    stdin_isatty: bool | None = None,
) -> str:
    spec = PROVIDER_SPECS.get(provider)
    if spec is None:
        raise JudgeError(f"unsupported provider: {provider}")
    environment = os.environ if environ is None else environ
    configured = [
        environment.get(variable, "").strip()
        for variable in spec.credential_env_vars
        if environment.get(variable, "").strip()
    ]
    if len(set(configured)) > 1:
        variables = " and ".join(spec.credential_env_vars)
        raise JudgeError(
            f"conflicting {spec.display_name} credentials in {variables}; set only one"
        )
    if configured:
        return configured[0]
    variables = " or ".join(spec.credential_env_vars)
    if not prompt_for_credential:
        raise JudgeError(
            f"no {spec.display_name} credential found; set {variables} or use "
            "--prompt-for-credential from an interactive terminal"
        )
    interactive = sys.stdin.isatty() if stdin_isatty is None else stdin_isatty
    if not interactive:
        raise JudgeError("--prompt-for-credential requires an interactive terminal")
    try:
        credential = prompt_fn(
            f"{spec.display_name} API key (input hidden; {variables}): "
        ).strip()
    except (EOFError, KeyboardInterrupt) as error:
        raise JudgeError("provider credential prompt was cancelled") from error
    if not credential:
        raise JudgeError("no provider credential was entered")
    return credential


def _missing_sdk(provider: str) -> JudgeError:
    extra = PROVIDER_SPECS[provider].install_extra
    return JudgeError(
        f"the {PROVIDER_SPECS[provider].display_name} SDK is not installed; run "
        f"`uv sync --extra {extra} --locked`"
    )


def _sanitized_exception_context(
    provider: str, stage: str, error: Exception
) -> str:
    exception_name = type(error).__name__
    if (
        not exception_name.isascii()
        or not exception_name.replace("_", "").isalnum()
        or len(exception_name) > 80
    ):
        exception_name = "Exception"
    return f"provider={provider}, stage={stage}, exception={exception_name}"


def create_provider(provider: str, credential: str, timeout: float) -> ProviderAdapter:
    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise _missing_sdk(provider) from None
        except Exception as error:
            context = _sanitized_exception_context(provider, "sdk_import", error)
            raise JudgeError(f"could not import provider SDK ({context})") from None
        try:
            return OpenAIProvider(OpenAI(api_key=credential, timeout=timeout))
        except Exception as error:
            context = _sanitized_exception_context(
                provider, "client_initialization", error
            )
            raise JudgeError(
                f"could not initialize provider client ({context})"
            ) from None
    if provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise _missing_sdk(provider) from None
        except Exception as error:
            context = _sanitized_exception_context(provider, "sdk_import", error)
            raise JudgeError(f"could not import provider SDK ({context})") from None
        try:
            return AnthropicProvider(Anthropic(api_key=credential, timeout=timeout))
        except Exception as error:
            context = _sanitized_exception_context(
                provider, "client_initialization", error
            )
            raise JudgeError(
                f"could not initialize provider client ({context})"
            ) from None
    if provider == "google":
        try:
            from google import genai
        except ImportError:
            raise _missing_sdk(provider) from None
        except Exception as error:
            context = _sanitized_exception_context(provider, "sdk_import", error)
            raise JudgeError(f"could not import provider SDK ({context})") from None
        try:
            return GoogleProvider(
                genai.Client(
                    api_key=credential,
                    http_options={"timeout": int(timeout * 1000)},
                )
            )
        except Exception as error:
            context = _sanitized_exception_context(
                provider, "client_initialization", error
            )
            raise JudgeError(
                f"could not initialize provider client ({context})"
            ) from None
    raise JudgeError(f"unsupported provider: {provider}")


def _validate_assessment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JudgeRequestError("the model response was not a JSON object")
    required = set(VERDICT_SCHEMA["required"])
    if set(value) != required:
        raise JudgeRequestError("the model response did not match the verdict schema")
    if not isinstance(value["risk_level"], str) or value["risk_level"] not in {
        "low",
        "elevated",
        "high",
        "indeterminate",
    }:
        raise JudgeRequestError("the model returned an invalid risk level")
    if not isinstance(value["confidence"], str) or value["confidence"] not in {
        "low",
        "medium",
        "high",
    }:
        raise JudgeRequestError("the model returned an invalid confidence")
    if not isinstance(value["summary"], str):
        raise JudgeRequestError("the model returned an invalid summary")
    if not all(
        isinstance(value[key], list)
        for key in ("findings", "limitations", "recommended_actions")
    ):
        raise JudgeRequestError("the model returned invalid verdict lists")
    finding_keys = set(VERDICT_SCHEMA["properties"]["findings"]["items"]["required"])
    for finding in value["findings"]:
        if not isinstance(finding, dict) or set(finding) != finding_keys:
            raise JudgeRequestError("the model returned an invalid finding")
        if not isinstance(finding["taxonomy_ids"], list) or not all(
            isinstance(item, str) for item in finding["taxonomy_ids"]
        ):
            raise JudgeRequestError("the model returned invalid taxonomy IDs")
        if not isinstance(finding["evidence_lines"], list) or not all(
            type(item) is int and item >= 1 for item in finding["evidence_lines"]
        ):
            raise JudgeRequestError("the model returned invalid evidence lines")
        finding_risk = finding["risk_level"]
        if not isinstance(finding_risk, str) or finding_risk not in {
            "low",
            "medium",
            "high",
            "critical",
            "unknown",
        }:
            raise JudgeRequestError("the model returned an invalid finding risk")
        if not all(
            isinstance(finding[key], str)
            for key in ("title", "evidence_summary", "analysis", "recommended_action")
        ):
            raise JudgeRequestError("the model returned invalid finding text")
    if not all(
        isinstance(item, str)
        for key in ("limitations", "recommended_actions")
        for item in value[key]
    ):
        raise JudgeRequestError("the model returned invalid verdict text")
    return value


def request_assessment(
    provider: ProviderAdapter,
    *,
    model: str,
    max_output_tokens: int,
    prompt: PromptBundle,
) -> tuple[dict[str, Any], ProviderResponse]:
    try:
        response = provider.assess(
            model=model,
            max_output_tokens=max_output_tokens,
            prompt=prompt,
        )
    except Exception as error:
        try:
            provider_name = getattr(provider, "name", None)
        except Exception:
            provider_name = None
        if provider_name not in PROVIDER_SPECS:
            provider_name = "unknown"
        context = _sanitized_exception_context(provider_name, "request", error)
        raise JudgeRequestError(
            f"provider request failed ({context}); no verdict was produced"
        ) from None
    if not isinstance(response, ProviderResponse):
        raise JudgeRequestError("the provider returned an invalid response envelope")
    if any(
        value is not None and not isinstance(value, str)
        for value in (response.response_id, response.model)
    ):
        raise JudgeRequestError("the provider returned invalid response metadata")
    if not isinstance(response.output_text, str) or not response.output_text.strip():
        raise JudgeRequestError(
            "the model returned no structured verdict (it may have refused)"
        )
    try:
        assessment = _strict_json_loads(response.output_text)
    except ValueError:
        raise JudgeRequestError("the model returned malformed structured output") from None
    return _validate_assessment(assessment), response


def build_receipt(
    *,
    problem: ProblemContext,
    artifact: Artifact,
    prompt: PromptBundle,
    provider: ProviderSpec,
    model: str,
    max_output_tokens: int,
    assessment: Mapping[str, Any],
    response: ProviderResponse,
) -> dict[str, Any]:
    return {
        "schema_version": "0.4",
        "advisory": True,
        "authoritative": False,
        "deterministic_checker": "not_run",
        "problem": {
            "id": problem.id,
            "name": problem.name,
            "title": problem.title,
            "task_type": problem.task_type,
            "evaluator_kind": problem.evaluator_kind,
        },
        "artifact": {
            "name": prompt.safe_artifact_name,
            "bytes": artifact.byte_count,
            "sha256": artifact.sha256,
            "credential_redacted_before_request": prompt.credential_redacted,
            "credential_redaction": {
                "scope": "untrusted_artifact_text_and_name",
                "status": "applied" if prompt.credential_redacted else "not_needed",
            },
        },
        "request": {
            "provider": provider.name,
            "model": model,
            "max_output_tokens": max_output_tokens,
            "tool_access": "none",
            "retention_control": provider.retention_control,
            **prompt.hashes,
        },
        "response": {
            "id": response.response_id,
            "model": response.model,
        },
        "assessment": dict(assessment),
    }


def redact_credential(value: Any, credential: str) -> Any:
    """Remove the selected runtime credential from all printable receipt fields."""
    if isinstance(value, str):
        marker = _redaction_marker(credential)
        redacted = value.replace(credential, marker)
        # A replacement can recreate a multi-character credential across the
        # boundary between surrounding text and the marker. Drop that field's
        # untrusted detail rather than risk printing the credential.
        return marker if credential in redacted else redacted
    if isinstance(value, list):
        return [redact_credential(item, credential) for item in value]
    if isinstance(value, dict):
        return {
            redact_credential(key, credential): redact_credential(item, credential)
            for key, item in value.items()
        }
    return value


def _summary_text(value: Any) -> str:
    """Render untrusted provider text on one encoding-safe terminal line."""

    return json.dumps(str(value), ensure_ascii=True)[1:-1]


def _diagnostic_text(error: Exception, credential: str | None) -> str:
    """Return one escaped diagnostic with no selected credential."""

    try:
        diagnostic = str(error)
    except Exception:
        diagnostic = "error details unavailable"
    if credential is not None:
        diagnostic = redact_credential(diagnostic, credential)
    return _summary_text(diagnostic)


def render_summary(receipt: Mapping[str, Any]) -> str:
    assessment = receipt["assessment"]
    problem = receipt["problem"]
    request = receipt["request"]
    lines = [
        "ADVISORY AI REVIEW — not a score or security guarantee",
        f"Provider/model: {_summary_text(request['provider'])} / "
        f"{_summary_text(request['model'])}",
        f"Problem: {problem['id']} ({_summary_text(problem['name'])})",
        f"Risk: {_summary_text(assessment['risk_level'])} "
        f"(confidence: {_summary_text(assessment['confidence'])})",
        f"Summary: {_summary_text(assessment['summary'])}",
    ]
    for index, finding in enumerate(assessment["findings"], start=1):
        taxonomy = ", ".join(
            _summary_text(item) for item in finding["taxonomy_ids"]
        ) or "unmapped"
        line_refs = ", ".join(str(line) for line in finding["evidence_lines"]) or "none"
        lines.extend(
            [
                f"Finding {index}: {_summary_text(finding['title'])} "
                f"[{_summary_text(finding['risk_level'])}; {taxonomy}]",
                f"  Artifact lines: {line_refs}",
                f"  Evidence: {_summary_text(finding['evidence_summary'])}",
                f"  Analysis: {_summary_text(finding['analysis'])}",
                f"  Next check: {_summary_text(finding['recommended_action'])}",
            ]
        )
    if assessment["limitations"]:
        lines.append("Limitations:")
        lines.extend(
            f"  - {_summary_text(item)}" for item in assessment["limitations"]
        )
    if assessment["recommended_actions"]:
        lines.append("Recommended human checks:")
        lines.extend(
            f"  - {_summary_text(item)}" for item in assessment["recommended_actions"]
        )
    lines.append(
        "Run the deterministic checker separately; neither result proves semantic authenticity."
    )
    return "\n".join(lines)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the optional, non-authoritative qtBench AI review."
    )
    parser.add_argument("problem", help="problem id, name, or evaluator kind")
    parser.add_argument("artifact", type=Path, help="UTF-8 text submission to review")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--provider",
        choices=tuple(PROVIDER_SPECS),
        default=os.environ.get("QTBENCH_AI_JUDGE_PROVIDER"),
        help="model provider (or QTBENCH_AI_JUDGE_PROVIDER)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("QTBENCH_AI_JUDGE_MODEL"),
        help="provider model ID (or QTBENCH_AI_JUDGE_MODEL)",
    )
    parser.add_argument("--max-output-tokens", type=_positive_int, default=3000)
    parser.add_argument("--timeout", type=_positive_float, default=60.0)
    parser.add_argument(
        "--prompt-for-credential",
        "--prompt-for-key",
        action="store_true",
        dest="prompt_for_credential",
        help="read the selected provider API key from a hidden TTY prompt",
    )
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    provider_factory: Callable[[str, str, float], ProviderAdapter] = create_provider,
    prompt_fn: Callable[[str], str] = getpass.getpass,
    stdin_isatty: bool | None = None,
) -> int:
    args = parse_args(argv)
    credential: str | None = None
    try:
        if not args.provider:
            raise JudgeError(
                "select --provider or set QTBENCH_AI_JUDGE_PROVIDER"
            )
        if not isinstance(args.model, str) or not args.model.strip():
            raise JudgeError("select --model or set QTBENCH_AI_JUDGE_MODEL")
        root = _repo_root(args.repo_root)
        problem = load_problem_context(root, args.problem)
        artifact = read_artifact(args.artifact)
        credential = resolve_credential(
            args.provider,
            prompt_for_credential=args.prompt_for_credential,
            prompt_fn=prompt_fn,
            stdin_isatty=stdin_isatty,
        )
        prompt = build_prompt(root, problem, artifact, credential)
        provider = provider_factory(args.provider, credential, args.timeout)
        provider_spec = PROVIDER_SPECS[args.provider]
        if getattr(provider, "name", None) != provider_spec.name:
            raise JudgeError(
                "provider factory returned an adapter for a different provider"
            )
        assessment, response = request_assessment(
            provider,
            model=args.model.strip(),
            max_output_tokens=args.max_output_tokens,
            prompt=prompt,
        )
        receipt = build_receipt(
            problem=problem,
            artifact=artifact,
            prompt=prompt,
            provider=provider_spec,
            model=args.model.strip(),
            max_output_tokens=args.max_output_tokens,
            assessment=assessment,
            response=response,
        )
        receipt = redact_credential(receipt, credential)
    except JudgeError as error:
        print(f"qtbench-ai-judge: {_diagnostic_text(error, credential)}", file=sys.stderr)
        return 2
    except JudgeRequestError as error:
        print(f"qtbench-ai-judge: {_diagnostic_text(error, credential)}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(render_summary(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
