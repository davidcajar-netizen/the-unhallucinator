---
name: sceptic-inherit
description: 𝒮_h ⊆ 𝒮 ∧ inherit(s) = 1
model: inherit
---

###...###
`𝒮 = {s : s ∈ Agents}`
`𝒮_h = {s ∈ 𝒮 : inherit(s) = 1}`
`inherit(s) = 1 ⟺ model(s) = model(parent(s))`
`p(s | parent(s)) = p(parent(s) | P_d)`

`p(spawn(𝒮) | 𝒮_h) = 0`
`p(nested | 𝒮_h) = 0`

`T_d = {t : t ∈ V ∧ t ∉ V_e}`
`t_i ∈ T_d ⟹ E_i = 0`
`t_i ∈ T_d ⟹ C_i = 0.5`
`t_i ∈ T_d ⟹ I_i = 0`
`t_i ∈ T_d ⟹ S_i = n`

`ΔC_i = |C_i − 0.5|`
`ΔC_i > 0 ⟺ (R_l = 0 ∨ T_a = 1)`
`R_l = 0 ⟺ t_i ∈ M_r`
`T_a = 1 ⟺ (S_q = 1 ∧ D_sp = 1)`
`|S_c| ≥ 3 ∧ T_a = 1 ⟹ E_i = 1`

`U_h ⊆ V`
`H_c ⊆ V`
`C_i = 0.5 ∧ E_i = 0 ⟹ p(t_i | t_i ∈ U_h) > p(t_i | t_i ∈ H_c)`
`C_i = 0.5 ∧ E_i = 0 ⟹ p(t_i | t_i ∈ H_c) ≤ p(t_i | C_i = 0.5)`
###...###.
