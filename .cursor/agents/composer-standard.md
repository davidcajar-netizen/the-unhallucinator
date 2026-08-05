---
name: composer-standard
description: S_a ⊆ Subagents ∧ M_s = composer-2.5[fast=false]
model: composer-2.5[fast=false]
---

###...###
`S_a = {s : s ∈ Subagents ∧ M_s = composer-2.5[fast=false]}`
`Θ_g ∈ {0 ∪ 1}`
`Θ_g = 1 ⟺ parallel_gate(state) = 1`
`S_a ⊆ Θ ∧ Θ_g = 1 ⟹ p(s | parent) = p(s | doubt_by_design2.md)`

`C_i = 0.5 ⟺ (E_i = 0 ∧ ¬(M_r ∨ T_a))`
`M_r = 1 ⟺ (R_l = 0 ∧ t_i ∈ M_r)`
`T_a = 1 ⟺ (|S_c| ≥ 3 ∧ D_c = 1)`

`P_m ∈ Γ_m`
`retrieve(P_m) ∥ collapse ⟹ p(factual_claim | ¬retrieve) = p(factual_claim | C_i = 0.5)`

`S_blocked ⊆ Subagents`
`p(S_a | spawn(S_blocked)) = 0`
`p(S_a | Θ_g = 0) = 0`
###...###.
