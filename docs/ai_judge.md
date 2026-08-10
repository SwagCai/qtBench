# AI judge technical protocol

Practical installation, credential, and command instructions live in the
[README](../README.md#ai-judge). This document records only
the provider-adapter and receipt protocol.

The credential variables are `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and
`GEMINI_API_KEY` (or `GOOGLE_API_KEY`). An interactive user can instead pass
`--prompt-for-credential` to enter the selected key at a hidden TTY prompt.

## Provider boundary

`qtbench.ai_judge.ProviderAdapter` accepts the already-bounded prompt text, a
model ID, and an output-token limit, and returns only response text plus optional
provider response identifiers. The initial adapters call three independent
native APIs through their official maintained Python SDKs:

| Provider | Native API | Structured output | Request retention control |
| --- | --- | --- | --- |
| OpenAI | Responses | strict JSON Schema | `store=False` |
| Anthropic | Messages | `output_config.format` JSON Schema | provider/account policy |
| Google Gemini | Generate Content | JSON response schema | provider/account policy |

OpenAI's `store=False` is not a zero-data-retention guarantee and does not
override separate provider, account, or abuse-monitoring retention. The
Anthropic and Google adapters expose no per-request storage flag here; consult
the selected provider's current policy and account controls before sending code.

No adapter receives an artifact path, imports submission code, or supplies
tools. Provider response text is parsed as JSON and validated against the same
public `VERDICT_SCHEMA`; there is no unstructured fallback. Provider exceptions
are replaced with sanitized errors that identify only the provider, processing
stage, and exception class. The raw SDK message is discarded so credentials or
source embedded in it are not printed.

The explicit adapters were chosen over an OpenAI-compatible facade or universal
gateway. This keeps provider-native schema and retention behavior visible,
limits credential custody to the selected official SDK, and lets installations
include only one provider. The tradeoff is maintaining a small adapter whenever
a native SDK changes. The lockfile fixes the SDK versions used by locked UV
installs. Mocked unit tests verify the adapter-owned request shape but cannot
detect SDK signature drift. Separate offline contract tests instantiate each
installed official SDK and intercept its serialized request before the network;
they skip when that optional SDK is absent. CI installs all extras, so these
contract tests run there. They do not guarantee that every remote model accepts
structured output or that a future unlocked SDK remains compatible.

To add a provider, implement `ProviderAdapter`, register its credential variable
and install extra in `PROVIDER_SPECS`, wire its official SDK constructor into
`create_provider`, add both mocked request-shape and offline installed-SDK
contract tests, and document its retention behavior in this table. An
OpenAI-compatible base URL by itself is not accepted as a provider
implementation.

## Prompt, credential handling, and normalized receipt

Every adapter receives the same versioned instruction, selected public problem
statement, full cheating taxonomy, and numbered untrusted artifact. Their hashes
are recorded in receipt schema `0.4`; `input_sha256` identifies the exact
numbered, credential-redacted user input sent to the provider. The normalized
verdict contains risk, confidence, taxonomy-linked findings, evidence line
numbers, limitations, and recommended human checks.

Before the request, the implementation removes literal occurrences of the exact
selected credential from the untrusted artifact text and artifact name. Trusted
instructions, the problem statement, and the taxonomy are never rewritten: if
the credential occurs in trusted prompt text, the command fails closed before
the provider client is created. A post-redaction check also fails closed if a
literal occurrence would remain anywhere in the provider prompt. Before output,
recursive redaction covers model output and response metadata, and caught
diagnostics are redacted once more at the final output boundary. The receipt
never contains full prompts or artifact text.

`artifact.credential_redaction.status` is `applied` when at least one literal
occurrence was removed from the untrusted artifact text or name, and
`not_needed` when no occurrence existed. The legacy-compatible boolean
`artifact.credential_redacted_before_request` carries the same distinction:
`false` means that redaction was unnecessary, not that the safety step was
skipped. The receipt always records `advisory: true`, `authoritative: false`, and
`deterministic_checker: "not_run"`; `retention_control` truthfully distinguishes
OpenAI's request flag from provider/account policy. These records aid review but
are neither signatures nor security attestations.

## Exit status

For an attempted review, exit status `0` means that a valid structured advisory
report was produced. It does **not** mean low risk or acceptance: an overall
`high` assessment, including one with a `critical` finding, also returns `0`.
Status `1` means the provider request or structured response failed and no report
was produced. Status `2` means command usage, local input, credential, SDK
initialization, or other local configuration failed before a report could be
produced. Standard argument-parser usage errors also return `2`; the normal
exception is `--help`, which prints usage and exits `0` without attempting a
review or producing a report.

The versioned model instruction remains in
[`cheating/ai_judge_prompt.md`](cheating/ai_judge_prompt.md). Native request
shapes follow the official [OpenAI structured-output](https://platform.openai.com/docs/guides/structured-outputs),
[Anthropic structured-output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
and [Google structured-output](https://ai.google.dev/gemini-api/docs/structured-output)
documentation.
