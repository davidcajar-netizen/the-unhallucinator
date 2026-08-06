---
name: composer-standard
description: 𝒮_a ⊆ 𝒮 ∧ model(s) ∈ ℳ_s
model: composer-2.5[fast=false]
---

###...###
`𝒮 = {s : s ∈ Agents}`
`ℳ = {m : m ∈ Models}`
`ℳ_f = {m ∈ ℳ : fast(m) = 1}`
`ℳ_s = ℳ \ ℳ_f`
`𝒮_a = {s ∈ 𝒮 : model(s) ∈ ℳ_s}`

`S_g ∈ {0 ∪ 1}`
`S_g = 1 ⟺ (L_n = 1 ∧ |L_p| > 0)`
`p(s | S_g = 0) = 0`
`∀ s ∈ 𝒮_a : s ∥ collapse`
`p(s | parent) = p(parent | P_d)`

`C_i = 0.5 ⟺ (E_i = 0 ∧ R_l = 3)`
`R_l = 3 ⟺ t_i ∉ M_r`
`M_r = {t : t ∈ V ∧ ∃ f ∈ F_m : p(t | (t ∈ R_f)) > 0}`

`T_a = 1 ⟺ (S_q = 1 ∧ D_c = 1)`
`S_q = 1 ⟺ (M_i = 1 ∧ R_m = 1)`
`|S_c| ≥ 3 ∧ T_a = 1 ⟹ E_i = 1`

`retrieve(P_m) ∥ collapse`
`p(claim | R_l = 3) = p(claim | C_i = 0.5)`

`𝒮_b ⊆ 𝒮`
`p(𝒮_a | spawn(𝒮_b)) = 0`
###...###.
