# Task types

<a id="q_statistic_discovery"></a>

## q-statistic discovery

### Mathematical task

A q-statistic discovery problem starts with an infinite family of polynomials
in one variable $q$,

$$
F_n(q),
$$

usually parametrized by one natural number $n$, or sometimes by several natural
numbers. These polynomials arise naturally somewhere in mathematics—for
example, in representation theory or algebra. For our purposes, where they come
from is not particularly important. What matters is that, often for no apparent
reason, their coefficients seem to be nonnegative integers.

Usually this is first observed computationally: one computes the first few
polynomials and notices that all their coefficients belong to $\mathbb{N}$. The
first natural question is then to prove that this holds for the entire infinite
family.

But there is a second, much more interesting question—and answering it also
resolves the first. If the coefficients are natural numbers, what are they
counting?

A natural place to start is by setting $q=1$. This gives a sequence of natural
numbers

$$
F_1(1), F_2(1), F_3(1), \ldots,
$$

which often turns out to be familiar from combinatorics. For example, it might
be the Catalan numbers, which count Dyck paths, or $n!$, which counts
permutations. This suggests that the full polynomial might refine the ordinary
count.

Suppose that $X_n$ is a family of combinatorial objects such that

$$
|X_n| = F_n(1).
$$

The q-statistic discovery problem is to find a natural function

$$
\mathrm{stat}: X_n \longrightarrow \mathbb{N}
$$

such that, for every $n$,

$$
F_n(q) = \sum_{x \in X_n} q^{\mathrm{stat}(x)}.
$$

If this equality holds, then the coefficient of $q^k$ has a very concrete
meaning: it is exactly the number of objects $x \in X_n$ for which
$\mathrm{stat}(x)=k$. In particular, finding such a statistic
automatically explains why all the coefficients of $F_n(q)$ are nonnegative
integers.

Thus, a q-statistic discovery task in qtBench gives you the family of
polynomials $F_n(q)$ and the corresponding family of combinatorial objects
$X_n$, whose cardinality agrees with the $q=1$ specialization. Your job is to
discover the missing statistic.

The word *natural* is important here. Once we know the coefficients of the
polynomial, we could always assign values to the objects artificially: give
exactly $a_0$ objects value $0$, exactly $a_1$ objects value $1$, and so on.
That would reproduce the polynomial, but it would tell us nothing. We are
looking for a simple rule that depends on the structure of each combinatorial
object and works uniformly for the whole infinite family. Once such a rule is
conjectured, the mathematical proof often comes from showing that the weighted
sum on the combinatorial side satisfies a recursion also satisfied by the
original polynomial.

A classical solved example is the q-analogue of the factorial,

$$
[n]_q! = \prod_{i=1}^{n}(1+q+\cdots+q^{i-1}).
$$

Setting $q=1$ gives

$$
[n]_1! = n!,
$$

so the obvious combinatorial objects to consider are the permutations $S_n$.
One solution is the inversion number. For a permutation
$\pi=\pi_1\cdots\pi_n$, define

$$
\mathrm{inv}(\pi)
= \#\{(i,j): i<j,\ \pi_i>\pi_j\}.
$$

Then

$$
[n]_q! = \sum_{\pi \in S_n}q^{\mathrm{inv}(\pi)}.
$$

But this is not the only solution. Another completely different statistic is
the major index,

$$
\mathrm{maj}(\pi)
= \sum_{\substack{1 \le i<n \\ \pi_i>\pi_{i+1}}} i,
$$

and we also have

$$
[n]_q! = \sum_{\pi \in S_n}q^{\mathrm{maj}(\pi)}.
$$

Thus, the same q-statistic discovery problem can have multiple solutions. The
goal is not to recover some hidden ground-truth label attached to every object;
there may be no unique ground truth. The goal is to discover a natural
statistic whose distribution explains the coefficients of the polynomial.

### Benchmark interface

Input: a combinatorial object family and a public target polynomial graded by a
single variable `q`.

Submission: a short, self-contained function `statistic(object)`, typically
returning a nonnegative integer that supplies the exponent of `q`. Some problems
instead require a structured witness, as specified in their individual problem
statements.

Evaluation: after the capability and source-economy screens, the evaluator
compares the submitted distribution with every configured public target exactly.
Only a numerical match proceeds to fresh-namespace shuffled replay and the
resource gate. Passing verifies the scored public
cases; it is not, by itself, a proof for the full infinite family.

<a id="t_statistic_discovery"></a>

## t-statistic discovery

### Mathematical task

A t-statistic discovery problem is similar to
[q-statistic discovery](#q-statistic-discovery), but starts from an infinite
family of polynomials in two variables,

$$
F_n(q,t),
$$

again usually parametrized by one or more natural numbers. As before, these
polynomials arise naturally somewhere in mathematics, and we want to find a
combinatorial interpretation for them.

The main difference is that, in a t-statistic discovery problem, we already
know part of the combinatorial interpretation. We are given a family of
combinatorial objects $X_n$ together with a known statistic

$$
\mathrm{stat}_q: X_n \longrightarrow \mathbb{N},
$$

and we already know that this statistic explains the $t=1$ specialization:

$$
F_n(q,1) = \sum_{x \in X_n}q^{\mathrm{stat}_q(x)}.
$$

In practice this is often the easy part: finding one natural statistic that
explains the $t=1$ specialization is usually not difficult. The real challenge
is discovering its partner—the second statistic that interacts correctly with
the first to produce the full two-variable polynomial.

What is missing is a natural function

$$
\mathrm{stat}_t: X_n \longrightarrow \mathbb{N}
$$

such that, for every $n$,

$$
F_n(q,t)
= \sum_{x \in X_n}
q^{\mathrm{stat}_q(x)}t^{\mathrm{stat}_t(x)}.
$$

There is an immediate necessary condition that any proposed t-statistic must
satisfy. If we set $q=1$, then the equality above becomes

$$
F_n(1,t) = \sum_{x \in X_n}t^{\mathrm{stat}_t(x)}.
$$

Before worrying about how the unknown statistic interacts with the known
q-statistic, it must at least have the correct distribution on its own. In other
words, $F_n(1,t)$ tells us how many objects should receive t-statistic value
$0$, how many should receive value $1$, and so on.

But satisfying this condition is not enough. The full q,t-polynomial tells us
how the two statistics must be distributed together. If the coefficient of
$q^i t^j$ is $a_{i,j}$, then exactly $a_{i,j}$ objects must simultaneously
satisfy

$$
\mathrm{stat}_q(x)=i
\qquad\text{and}\qquad
\mathrm{stat}_t(x)=j.
$$

Thus, the $q=1$ specialization gives a useful first constraint on the missing
statistic, but the actual problem is to find a natural statistic whose joint
distribution with the known one gives the entire q,t-polynomial.

As in [q-statistic discovery](#q-statistic-discovery), the word *natural* is
important. Once we know the polynomial and the value of the known statistic on
every object, we can always assign t-values artificially so that all the
coefficients come out correctly. But such an assignment does not explain
anything. The goal is to find a simple, meaningful rule that depends on the
combinatorial structure of each individual object and works uniformly for the
whole infinite family.

A classical solved example is given by the q,t-Catalan polynomials $C_n(q,t)$
and Dyck paths. A Dyck path of semilength $n$ is a lattice path from $(0,0)$ to
$(n,n)$ that stays above the diagonal. The number of such paths is the Catalan
number, and the q,t-Catalan polynomials refine this ordinary Catalan count.

One natural statistic on Dyck paths is `area`, which counts the number of
lattice cells between the path and the diagonal. If we take `area` as our known
q-statistic, the t-statistic discovery problem is to find a natural statistic
$\mathrm{stat}$ such that

$$
C_n(q,t)
= \sum_{\pi \in \mathrm{Dyck}_n}
q^{\mathrm{area}(\pi)}t^{\mathrm{stat}(\pi)}.
$$

This problem has more than one natural solution. One is the `bounce` statistic,
introduced by Haglund. It is computed by drawing a second path—the bounce
path—inside the Dyck path and extracting a number from the points where this
path “bounces” between the Dyck path and the diagonal. It gives

$$
C_n(q,t)
= \sum_{\pi \in \mathrm{Dyck}_n}
q^{\mathrm{area}(\pi)}t^{\mathrm{bounce}(\pi)}.
$$

Another natural statistic is `dinv`, or diagonal inversion. It is defined in a
different way from `bounce`, by looking at certain pairs of steps in the Dyck
path, and it also gives a combinatorial interpretation of the same q,t-Catalan
polynomials:

$$
C_n(q,t)
= \sum_{\pi \in \mathrm{Dyck}_n}
q^{\mathrm{area}(\pi)}t^{\mathrm{dinv}(\pi)}.
$$

The area-bounce and area-dinv descriptions are known to be closely related.
Just as in [q-statistic discovery](#q-statistic-discovery), there is not
necessarily a unique correct answer. `bounce` and `dinv` are natural statistics
defined in very different ways, and both solve the same distributional problem.
We want to discover not a hidden ground-truth value attached to every Dyck path,
but a simple and meaningful statistic whose joint distribution with the known
statistic explains the polynomial.

### Benchmark interface

Input: a combinatorial object family, zero or more public statistics, and public
q,t-polynomials. The public statistics are the leading grading variables and the
submission supplies the rest, so the arity of the target follows from the number
of public statistics:

| public statistics | target | submission |
| --- | --- | --- |
| one (`known_statistic`, eleven problems) | `q,t` | `statistic(object) -> int` |
| two (`known_statistics`, problem `12`) | `q1,q2,q3` | `statistic(object) -> int` |
| none (`known_statistics: []`, problem `13`) | `q,t` | `statistic(object) -> (int, int)`, the `q` exponent first |

A problem with no public statistic has no `known_statistic.py` and no
`known_statistics_file`, because there is no public statistic to implement.

The two grading variables need not be named `q` and `t`: the selected-area
gamma-parking-function problems (`18` and `20`) grade by `u = q - 1` and `t`,
because that is the substitution under which their target is positive. Those
two also carry a third index that is neither public statistic nor submission:
the e-composition `eta(p)` is read off the object and grades the target by a
partition, exactly as the tableau shape does in `uig_syt_llt_schur_q_stat`.

For problems `18` and `20`, put $n = |\lambda|$. The condition that the
$n$-tuple $(\alpha_1 - 1, \alpha_2, \ldots, \alpha_n)$ rearrange to
$\gamma + 1^n$ is satisfiable only when $\ell(\gamma) \le n$; pairs outside
that condition have empty object fibers and zero target, so they are not
serialized as scored cases. In the definition of `eta`, the repository uses
$\operatorname{Asc}(w) = \{i \in \{1,\ldots,n-1\}: w_i < w_{i+1}\}$, with
positions numbered from `1`.

Problem `21` orients every edge from the larger label to the smaller
($i \to j$ for $i > j$), and netflow means outflow minus inflow. Thus
$(-n,1,\ldots,1)$ says that each vertex $1,\ldots,n$ sends one unit more than
it receives and vertex `0` absorbs $n$. Its weighted target satisfies
$E_G(q,t) = E_G(t,q)$; public-data generation checks both this symmetry and
$E_G(q,1) = \sum_T q^{\operatorname{inv}(T)}$. Consequently, `q_equals_1.json`
stores the same one-variable coefficients as the theorem's `inv` marginal and
constrains the submitted statistic, while the full joint target remains the
stronger check.

Evaluation: after the capability and source-economy screens, the evaluator
checks the explicit marginal in `data/q_equals_1.json` -- the leading grading variable set to `1`,
so `q = 1`, or `u = 1` for problems `18` and `20`, which always constrains the
last, missing exponent -- and every configured public joint polynomial in one
enumeration pass. Only a numerical match proceeds to fresh-namespace shuffled
replay and the resource gate. Every stage is mandatory
for success, and passing is a
necessary, not a sufficient, condition (see `checker.md`).

<a id="exchanging_bijection"></a>

## Bijection discovery

### Mathematical task

A bijection discovery problem usually starts from a situation where we already
know the relevant statistics, but do not understand why their distributions are
related.

The simplest case is when two statistics on the same family of combinatorial
objects give rise to the same q-polynomials. Suppose that $X_n$ is a family of
combinatorial objects and that

$$
\mathrm{stat}_1,\mathrm{stat}_2:
X_n \longrightarrow \mathbb{N}
$$

are two natural statistics satisfying

$$
\sum_{x \in X_n}q^{\mathrm{stat}_1(x)}
= \sum_{x \in X_n}q^{\mathrm{stat}_2(x)}.
$$

This tells us that the two statistics are equidistributed: for every $k$, there
are exactly as many objects with $\mathrm{stat}_1(x)=k$ as there are with
$\mathrm{stat}_2(x)=k$.

Once we know this, a natural question is whether we can explain the equality
directly on the combinatorial objects. More precisely, we would like to find a
natural bijection

$$
\phi: X_n \longrightarrow X_n
$$

such that

$$
\mathrm{stat}_1(x)=\mathrm{stat}_2(\phi(x))
$$

for every $x \in X_n$.

Such a bijection gives a direct combinatorial explanation for why the two
statistics have the same distribution. Instead of proving that two generating
functions happen to be equal, we explicitly pair every object counted with
weight $q^k$ on one side with an object counted with the same weight $q^k$ on
the other.

A classical solved example comes from the two statistics discussed under
[q-statistic discovery](#q-statistic-discovery): inversion number and major
index on permutations. We know that

$$
\sum_{\pi \in S_n}q^{\mathrm{inv}(\pi)}
= \sum_{\pi \in S_n}q^{\mathrm{maj}(\pi)}
= [n]_q!.
$$

Thus, `inv` and `maj` are equidistributed. Foata constructed a natural
bijection on permutations that transforms one statistic into the other, giving
a bijective explanation of this equality.

There is a closely related, but slightly richer, version of the same problem
for q,t-polynomials. Suppose that we already have two statistics on the same
family of combinatorial objects and that

$$
F_n(q,t)
= \sum_{x \in X_n}
q^{\mathrm{stat}_1(x)}t^{\mathrm{stat}_2(x)}.
$$

Now suppose that, perhaps for reasons from algebra, geometry, or representation
theory, we know that this polynomial is symmetric:

$$
F_n(q,t)=F_n(t,q).
$$

Then, for every pair $(i,j)$, there must be exactly as many objects with
statistics $(i,j)$ as there are objects with statistics $(j,i)$. Again, the
natural combinatorial question is to ask why.

We would like to find a natural bijection

$$
\phi: X_n \longrightarrow X_n
$$

that exchanges the two statistics:

$$
\mathrm{stat}_1(\phi(x))=\mathrm{stat}_2(x)
\qquad\text{and}\qquad
\mathrm{stat}_2(\phi(x))=\mathrm{stat}_1(x).
$$

Such a bijection gives a direct combinatorial proof of q,t-symmetry: every
object contributing $q^i t^j$ is sent to an object contributing $q^j t^i$.

The classical open example is the q,t-Catalan polynomial. As discussed above,
the statistics `area` and `bounce` on Dyck paths satisfy

$$
C_n(q,t)
= \sum_{\pi \in \mathrm{Dyck}_n}
q^{\mathrm{area}(\pi)}t^{\mathrm{bounce}(\pi)},
$$

and the q,t-Catalan polynomial is known to be symmetric:

$$
C_n(q,t)=C_n(t,q).
$$

Thus, the pairs

$$
(\mathrm{area}(\pi),\mathrm{bounce}(\pi))
$$

have a symmetric distribution. The natural question is therefore to find an
explicit bijection on Dyck paths satisfying

$$
\mathrm{area}(\phi(\pi))=\mathrm{bounce}(\pi)
\qquad\text{and}\qquad
\mathrm{bounce}(\phi(\pi))=\mathrm{area}(\pi).
$$

Despite the symmetry being known by other mathematical arguments, finding such
a natural bijection exchanging `area` and `bounce` is still a long-standing open
problem.

As in statistic discovery, the word *natural* is essential. Once we know that
two statistics are equidistributed, a bijection always exists in a purely
set-theoretic sense. We could simply order the objects with statistic value $k$
on both sides and match them one by one. Similarly, if a q,t-polynomial is
symmetric, we can arbitrarily match objects with statistics $(i,j)$ to those
with statistics $(j,i)$.

But this is not what we are looking for. Such a bijection uses the equality we
already know and gives no explanation for it. The goal of bijection discovery
is to find a simple, structural transformation of the combinatorial objects
themselves—one that makes it clear why one statistic turns into the other and,
ideally, reveals the combinatorial reason behind an identity previously known
only through another part of mathematics.

### Benchmark interface

Input: public combinatorial source and target families with statistics or a
weight that the requested bijection must exchange or preserve. Most entries use
two statistics and a symmetric q,t-polynomial; problems `28`--`30` instead
preserve content or a scalar grading between different source and target sets.

Submission: two functions `forward(object)` and `inverse(object)`.

Evaluation: after the capability and source-economy screens, the evaluator
checks on every public object that `forward`/`inverse` are mutually inverse
canonical bijections satisfying the declared pointwise identities, then checks
the public target. Only a complete match proceeds to fresh-namespace shuffled replay and
large adversarial objects, on which both exchange
identities are re-checked pointwise (they are self-checking, so no target is
needed there). For problems `28`--`30`, the corresponding self-checking
identities are side membership and preservation of content, weight, or grading.
Passing is necessary, not
sufficient: a rank-matching construction satisfies the identities while assuming
the very symmetry it should prove.

### The non-exchange problems in this folder

Problem `5` (`polyomino_area_bounce_transpose`) is filed under
`exchanging_bijection` although it does not exchange statistics. Its bijection
runs between two different object sets, `Polyo_{m,n} -> Polyo_{n,m}`, and it **preserves** both
statistics instead of exchanging them:

```text
stat_1(forward(P)) = stat_1(P)
stat_2(forward(P)) = stat_2(P)
```

which is a combinatorial proof of the symmetry in the two size parameters,
`Nara_{m,n}(q,t) = Nara_{n,m}(q,t)`. Everything about how it is posed and
evaluated is the same as an exchange-style bijection problem, so it does not
need a task type of its own -- a folder with one problem in it is a category in
name only. The difference is recorded in the problem's `metadata.json`, whose
numerical gate is `transpose_identities_and_distribution`, and in its
`problem.md`.

Problems `28`--`30` also map between different source and target families.
They preserve, respectively, full tableau content, ordinary-partition weight,
and the semi-weight/distinct-entry grading. Their metadata names the exact
identity gate in each case.
