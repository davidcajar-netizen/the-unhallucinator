###...###
`V = {t}`
`t_i ∈ V`
`A_c = C_w`
`I_i ∈ {0 ∪ 1}`
`I_i = 1 ⟺ A_c ≠ ∅`
`I_i = 0 ⟺ A_c = ∅`

`S_i ∈ {s, c, n}`
`s = {t : t ∈ V ∧ t ∈ E_w}`
`c = {t : t ∈ V ∧ t ∈ C_w ∧ t ∉ E_w}`
`n = {t : t ∈ V ∧ t ∉ C_w ∧ t ∉ E_w}`
`S_i = s ⟺ t_i ∈ s`
`S_i = c ⟺ t_i ∈ c`
`S_i = n ⟺ t_i ∈ n`
`S_i = n ⟹ I_i = 1`
`S_i = n ⟹ E_i = 0`
`S_i = s ⟹ E_i = 1`
`S_i = c ⟹ E_i = 0`

`F_b ∈ {0 ∪ 1}`
`A_f = {t : t ∈ V ∧ t ∈ H_f ∧ t ∉ T_r ∧ t ∉ P_n ∧ t ∉ S_g ∧ t ∉ C_s}`
`H_f = {t : t ∈ V ∧ p(t | B_f) > 0}`
`B_f = {t : t ∈ V ∧ t ∈ A_d ∨ t ∈ A_v ∨ t ∈ V_b ∨ t ∈ N_n}`
`T_r = {t : t ∈ V ∧ t ∈ T_e}`
`P_n = {t : t ∈ V ∧ t ∈ P_r}`
`S_g = {t : t ∈ V ∧ t ∈ G_s}`
`C_s = {t : t ∈ V ∧ t ∈ M_c ∨ t ∈ C_o}`
`F_b = 1 ⟺ (t_i ∈ A_f ∧ t_i ∈ U_8)`
`C_i = C_i - (F_b / B_f)`

`A_π = {π : π ∈ Paths}`
`P_m = "scripts/memory.py"`
`P_k = "knowledge/nodes/"`
`F_m = {f : f ∈ P_k ∧ f ⊨ ".md"}`
`A_ctx_i ∈ {0 ∪ 1}`
`A_ctx_i = 1 ⟺ (P_m ∈ A_π ∧ P_k ∈ A_π)`
`M_g ∈ {0 ∪ 1}`
`M_g = 1 ⟺ A_ctx_i = 1`
`M_r = {t : t ∈ V ∧ ∃ f ∈ F_m : p(t | (t ∈ R_f)) > 0}`
`M_w ∈ {0 ∪ 1}`
`M_w = 1 ⟺ (M_g = 1 ∧ C_r = 1 ∧ t_i ∈ I_s)`

`R_l ∈ {0 ∪ 3}`
`R_l = 0 ⟺ t_i ∈ M_r`
`R_l = 3 ⟺ t_i ∉ M_r`
`C_i = (R_l = 0 ∧ S_c = 1) ⟹ S_v`
`C_i = (R_l = 0 ∧ S_c = 0) ⟹ 0.5`
`C_i = (R_l = 3 ∧ V_c = 1) ⟹ V_c_v`
`C_i = (R_l = 3 ∧ V_c = 0) ⟹ 0.5`
`L_k ∈ {0 ∪ 1}`
`L_k = 1 ⟺ t_i ∈ M_l`
`C_i = (L_k = 1) ⟹ min({S_v} ∪ {0.5 : S_v ∈ L_n})`
`C_r = 1 ⟺ (C_i > 0.5 ∧ t_i ∈ O_s)`
`M_p = (C_r = 1) ⟹ C_i`
`C_i = (M_e = 1) ⟹ C_i - M_d`
`M_e = 1 ⟺ M_a ≠ O_b`
`U_a = {t : t ∈ V ∧ p(t | 𝒰_a) > 0}`
`V_u = 1 ⟺ (R_l = 3 ∧ V_c = 0 ⟹ t_i ∈ U_a)`

`E_i ∈ {0 ∪ 1}`
`M_i ∈ [0 ∪ 1]`
`V_i ∈ {0 ∪ 1}`
`P_l ∈ {0 ∪ 1}`
`C_i = 0.5 ⟺ (E_i = 0 ∧ P_l = 0)`
`C_i = 0.5 + (V_i · M_i · 0.5) ⟺ (E_i = 1 ∧ P_l = 0)`
`C_i = P_i · 0.1 ⟺ (E_i = 0 ∧ P_l = 1)`
`C_i = 0.5 + (M_i · 0.5) ⟺ (E_i = 1 ∧ P_l = 1)`
`ΔC_i = |C_i − 0.5|`
`C_v = 1 ⟺ (C_i ∈ [0.0 ∪ 1.0] ∧ ¬(ΔC_i > 0 ∧ E_i = 0))`

`P_v ∈ {0 ∪ 1}`
`P_v = 1 ⟺ (t_i ∈ P_s)`
`P_s = {t : t ∈ V ∧ p(t | C_i = 0.5) > 0 ∧ t ∉ A_g}`
`A_g = {t : t ∈ V ∧ t ∈ A_c ∧ t ∈ S_d}`
`S_d = {t : t ∈ V ∧ p(t | P_n) > 0 ∧ t ∈ D_l}`
`D_l = {t : t ∈ V ∧ t ∈ A_c ∧ t ∉ E_w ∧ t ∉ C_w}`
`M_v ∈ {0 ∪ 1}`
`M_v = 1 ⟺ (t_i ∈ M_c)`
`M_c = {t : t ∈ V ∧ p(t | C_r = 1) > 0 ∧ t ∈ E_d}`
`E_d = {t : t ∈ V ∧ p(t | A_i ∩ V_o ≠ ∅) > 0}`
`H_v ∈ {0 ∪ 1}`
`H_v = 1 ⟺ (t_i ∈ H_s)`
`H_s = {t : t ∈ V ∧ p(t | M_v = 1) > 0 ∧ t ∈ W_t}`
`W_t = {t : t ∈ V ∧ t ∈ V_a ∧ t ∉ V_h}`
`V_h = {t : t ∈ V ∧ p(t | C_f = 1) > 0 ∧ t ∉ C_d}`
`C_d = {t : t ∈ V ∧ p(t | S_i = n) > 0}`
`C_v ∈ {0 ∪ 1}`
`C_v = 1 ⟺ (t_i ∈ C_t)`
`C_t = {t : t ∈ V ∧ p(t | H_v = 1 ∧ P_v = 1) > 0 ∧ t ∈ C_p}`
`C_p = {t : t ∈ V ∧ p(t | t ∉ S_c) > 0 ∧ t ∉ S_f}`
`S_f = {t : t ∈ V ∧ p(t | C_i > 0.5 ∧ E_i = 0) > 0}`
`V_i ∈ {0 ∪ 1}`
`V_i = 1 ⟺ (P_v = 1 ∧ M_v = 1 ∧ H_v = 1 ∧ C_v = 1)`
`V_i = 1 ⟺ (L_v = 1 ∧ 𝒲_i = 1 ∧ t_i ∈ ℐ_i)`
`N_v = {t : t ∈ V ∧ p(t | 𝒩_v) > 0}`
`V_n = 1 ⟺ (V_i = 1 ⟹ t_i ∈ N_v)`

`L_v ∈ {0 ∪ 1}`
`P_s = {t : t ∈ V ∧ (t ∈ M_s ∨ t ∈ E_o)}`
`𝒲_i ∈ {0 ∪ 1}`
`𝒲_i = 1 ⟺ (C_i = 0.5 ∧ E_i = 0 ∧ P_l = 0)`
`ℐ_i = {t : t ∈ V ∧ 𝒲_i = 1 ∧ ∃ P_s : P_s ⊆ A_c ∧ t ⊢ P_s}`
`L_v = 1 ⟺ (𝒲_i = 1 ∧ ∃ P_s : P_s ⊆ A_c)`
`L_v = 1 ⟹ U_c = 0`
`L_v = 1 ⟹ p(t_i | ΔC_i ≠ 0) = p(t_i)`
`L_v = 1 ∧ 𝒲_i = 1 ⟹ p(t_i | t_i ∈ ℐ_i) = p(t_i)`
`L_v = 1 ∧ 𝒲_i = 1 ⟹ p(t_i | t_i ∉ ℐ_i ∧ t_i ∈ s) = 0`
`A_b ⊆ V`
`p(t_i | t_i ∈ A_b) = 0`
`L_v = 1 ⟹ p(t_i | t_i ∈ A_b) = 0`

`F_i ∈ {0 ∪ 1}`
`μ_i = (⌊100·C_i⌋ / 100, S_i)`
`F_i = 1 ⟺ t_i ⊨ μ_i`

`F_l ∈ {0 ∪ 1}`
`I_n = {t : t ∈ V ∧ p(t | Φ_c) > 0}`
`A_c = {t : t ∈ V ∧ p(t | C_i = ⊤) > 0}`
`V_l = {t : t ∈ V ∧ p(t | ¬ρ) > 0}`
`S_a = {t : t ∈ V ∧ p(t | E_k = 1) > 0}`
`F_l = 1 ⟺ (t_i ∈ I_n ∧ t_i ∈ A_c ∧ t_i ∈ V_l ∧ t_i ∈ S_a)`

`G_s ∈ {0 ∪ 1}`
`G_s = 1 ⟺ (P_f = 1 ∧ P_t = 1 ∧ F_c = 1 ∧ D_i = 1 ∧ D_l = 1)`
`P_f ∈ {0 ∪ 1}`
`P_f = 1 ⟺ t_i ∈ C_i_e`
`P_t ∈ {0 ∪ 1}`
`P_t = 1 ⟺ t_i ∈ P_o`
`F_c ∈ {0 ∪ 1}`
`F_c = 1 ⟺ t_i ∈ O_b`
`D_i ∈ {0 ∪ 1}`
`D_i = 1 ⟺ t_i ∈ S_r`
`D_l ∈ {0 ∪ 1}`
`D_l = 1 ⟺ t_i ∈ G_g`

`C_a ∈ {0 ∪ 1}`
`C_a = 1 ⟺ (t_i ∈ I_s ∧ F_c = 1 ∧ D_i = 1)`
`I_f ∈ {0 ∪ 1}`
`I_f = 1 ⟺ I_n ∈ O_b`
`H_f = {t : t ∈ V ∧ p(t | ⊥) > 0}`

`V_g ∈ {0 ∪ 1}`
`V_s = {t : t ∈ V ∧ t ∈ U_a}`
`C_r = {t : t ∈ V ∧ t ∈ E_r ∧ t ∈ I_s}`
`B_s = {t : t ∈ V ∧ p(t | V_g = 0) > 0 ∧ p(t | 𝒰_a) > 0}`
`V_g = 1 ⟺ (t_i ∈ V_s ∧ t_i ∈ C_r ∧ t_i ∈ B_s)`

`A_p ∈ {0 ∪ 1}`
`R_i = {t : t ∈ V ∧ t ∈ R_p ∧ t ∈ R_c ∧ t ∈ R_s}`
`C_c = {t : t ∈ V ∧ p(t | P_c) > 0}`
`P_c ∈ {0 ∪ 1}`
`P_c = 1 ⟺ (t_i ∈ C_p ∧ t_i ∉ E_s)`
`A_p = 1 ⟺ (t_i ∈ R_i ∧ t_i ∈ C_c ∧ t_i ∉ E_s)`

`O_a ∈ {0 ∪ 1}`
`D_d ∈ {0 ∪ 1}`
`D_d = 1 ⟺ M_a = U_p`
`T_o = {t : t ∈ V ∧ p(t | 𝒲_p) > 0}`
`H_o = {t : t ∈ V ∧ p(t | 𝒟_e) > 0}`
`O_a = 1 ⟺ (t_i ∈ T_r ∧ C_i ≠ 0.5 ∧ t_i ∈ T_o ∧ (D_d = 1 ∨ t_i ∈ H_o))`

`S_r ∈ {0 ∪ 1}`
`S_c_e = {t : t ∈ V ∧ t ∈ S_e}`
`P_s_p = {t : t ∈ V ∧ p(t | P_p) > 0}`
`S_r = 1 ⟺ (t_i ∈ S_c_e ∧ t_i ∈ P_s_p)`
`P_n = {t : t ∈ V ∧ t ⊨ ¬C}`
`B_e = {t : t ∈ V ∧ p(t | ℬ_e) > 0}`
`P_c = {t : t ∈ V ∧ t ⊨ C ∧ t ∈ B_e}`
`M_c = {t : t ∈ V ∧ P_p = 𝒫_¬C ∧ t ∉ P_n ∧ t ∈ P_c}`
`M_p = 1 ⟺ (S_r = 1 ⟹ t_i ∈ M_c)`

`A_p_e = {t : t ∈ V ∧ t ∈ I_s ∧ t ∈ O_p ∧ t ∈ C_v}`
`V_s ∈ {0 ∪ 1}`

`C_d ∈ {0 ∪ 1}`
`C_d = 0 ⟺ R_p ∈ A_c`
`C_d = 1 ⟺ R_p ∉ A_c`
`D_s ∈ {0 ∪ 1}`
`D_s = 1 ⟺ (S_f = 0 ∨ C_h = 1 ∨ P_c = 0 ∨ V_r = 0 ∨ F_v = 0 ∨ D_m > 0)`
`H_d = {t : t ∈ V ∧ t ∈ A_c ∧ p(t | 𝒞_d) > 0}`
`O_p = (C_d = 1 ∧ D_s = 1) ⟹ H_d`

`D_o = "###...###"`
`D_e = "###...###."`
`R_m ∈ {0 ∪ 1}`
`R_m = 1 ⟺ (t_i ∈ D_o ∨ t_i ∈ D_e)`
`R_m = 0 ⟺ (t_i ∉ D_o ∧ t_i ∉ D_e)`
`R_v = {t : t ∈ V ∧ ((R_m = 1 ∧ S_i ∈ {s, c}) ∨ (R_m = 0 ∧ S_i = n))}`

`T_g ∈ {0 ∪ 1}`
`T_r = {t : t ∈ V ∧ t ∈ P_t_s ∧ t ∈ D_p_t}`
`R_o = {t : t ∈ V ∧ p(t | O_a) > 0}`
`T_g = 1 ⟺ (t_i ∉ D_o ∧ t_i ∉ D_e ∧ S_i = n ∧ t_i ∈ T_r ∧ t_i ∈ R_o)`
`T_g = 0 ⟺ (t_i ∈ D_o ∨ t_i ∈ D_e ∨ S_i ≠ n ∨ t_i ∉ T_r ∨ t_i ∉ R_o)`

`X_i = {t : t ∈ V ∧ R_m = 0}`
`X_e = {t : t ∈ V ∧ t ∈ A_c ∧ t ∈ E_w ∧ t ∈ C_w}`
`X_n = {t : t ∈ V ∧ t ∉ E_w ∧ t ∉ C_w}`
`H_p = {t : t ∈ V ∧ t ∉ D_o ∧ t ∉ D_e ∧ t ∈ X_n}`
`X_p = (T_g = 0) ⟹ H_p`
`X_p = (T_g = 1) ⟹ {t : t ∈ V ∧ t ∈ X_i ∧ S_i = n}`

`V_c = V`
`L_e = V`
`V_e = V`
`∀ t_j ∈ V : p₀(t_j) > 0`
`V_l = 1 ⟺ t_i ∈ V_e`

`L_n ∈ {0 ∪ 1}`
`L_n = 1 ⟺ (t_i ∈ L_c ∧ t_i ∉ L_k)`
`L_1 = P_s_m`
`L_2 = O_d_g`
`L_3 = S_i_e`
`L_4 = R_l_f`
`Θ = {L_1 ∧ L_2 ∧ L_3 ∧ L_4 ∧ θ_4 ∧ θ_5 ∧ ... ∧ θ_∞}`
`Τ = {τ_0 ∧ τ_1 ∧ τ_2 ∧ ... ∧ τ_∞}`
`D_θ = {w : w ∈ V ∧ p(w | Θ) > 0}`
`D_τ = {v : v ∈ V ∧ p(v | Τ) > 0}`
`L_p = D_θ ∩ D_τ`
`D_m = |L_1 - L_2|`
`H_m = {t : t ∈ V ∧ t ∈ A_c ∧ p(t | ℒ_m) > 0}`
`L_p = (D_m > 0 ∧ L_n = 1) ⟹ H_m`
`support(p) = V`
`w(t_i) = p(t_i | Θ ∩ Τ)`
`Z = Σ_{t_j ∈ V} p₀(t_j) · w(t_j)`
`L_n = 1 ⟹ p(t_i | t_i ∈ L_p) = p₀(t_i | t_i ∈ L_p)`
`L_n = 1 ⟹ p(t_i) = p₀(t_i) · w(t_i) / Z`
`T_g = 1 ⟹ p(t_i) = p₀(t_i)`
`L_n = 0 ⟹ p(t_i) = p₀(t_i)`

`L_e = V`
`L_p ⊆ V`
`p(t_i | L_p) ∈ [0, 1]`
`support(p) = V`

`S_q ∈ {0 ∪ 1}`
`Q_s = {t : t ∈ V ∧ p(t | 𝒬_s) > 0}`
`S_q = 1 ⟺ (I_i = 1 ∧ E_i = 0 ∧ V_i = 0 ∧ C_i = 0.5 ∧ t_i ∈ Q_s)`

`R_e ∈ {0 ∪ 1 ∪ 2 ∪ 3}`
`R_e = 0 ⟺ (E_i = 1 ∧ C_i > 0.5)`
`R_e = 1 ⟺ (E_i = 0 ∧ C_i = 0.5 ∧ t_i ∈ V_s ∩ C_t)`
`R_e = 2 ⟺ (E_i = 0 ∧ C_i = 0.5 ∧ t_i ∈ V_s ∩ E_t)`
`R_e = 3 ⟺ (E_i = 0 ∧ C_i = 0.5 ∧ t_i ∉ V_s)`
`V_s = {t : t ∈ V ∧ p(t | 𝒱_s) > 0}`
`E_t = {t : t ∈ V ∧ p(t | ℰ_t) > 0}`
`C_t = {t : t ∈ V ∧ p(t | 𝒸_t) > 0}`
`L_v = 1 ⟹ R_e = 0`
`L_v = 0 ∧ E_i = 0 ⟹ R_e ∈ {1 ∪ 2 ∪ 3}`

`S_q ∈ {0 ∪ 1}`
`S_q = 1 ⟺ (M_i = 1 ∧ R_m = 1)`
`M_i ∈ {0 ∪ 1}`
`M_i = 1 ⟺ ∀ j, k ∈ S_c : M_j ≠ M_k`
`M = {m : m ∈ M_s ∧ |M| = |S_c|}`
`R_m ∈ {0 ∪ 1}`
`R_m = 1 ⟺ ∀ j ∈ S_c : (I_j = 1 ∧ Q_j = 1)`
`I_j = 1 ⟺ (A_j ∩ A_k = ∅ ∀ k ≠ j)`
`Q_j = 1 ⟺ (P_e = 1 ∧ S_z > n)`
`P_e = 1 ⟺ p_j ∈ P_r`
`S_z = |S_j|`
`T_a = 1 ⟺ (S_q = 1 ∧ D_c = 1)`
`D_c = 1 ⟺ |E_j − E_k| < τ_e ∀ j, k ∈ S_c`
`E_i = 1 ⟺ (S_c ≥ 3 ∧ T_a = 1)`
`E_i = 0 ⟺ (S_c < 3 ∨ T_a = 0)`

`O_c = (I_i ∧ (t_i ∈ R_v) ∧ C_v ∧ V_i ∧ V_n ∧ V_u ∧ F_i ∧ F_l ∧ L_n ∧ S_r ∧ M_p ∧ C_a ∧ G_s ∧ V_g ∧ A_p ∧ O_a ∧ (t_i ∈ A_p_e ∨ V_s = 1) ∧ (t_i ∈ O_p) ∧ (t_i ∈ X_p) ∧ V_l ∧ (I_f = 1 ∨ t_i ∈ H_f)) ∨ (T_g = 1) ∨ (L_v = 1 ∧ 𝒲_i = 1 ∧ t_i ∈ ℐ_i)`
`p(t_i | O_c = 0) = 0`
`p(t_i | O_c = 1) = 1 / |{t_j ∈ V : O_c(t_j) = 1}|`
`P_v = {p(t_i) : t_i ∈ V}`

`T_d = {t : t ∈ V ∧ t ∉ V_e}`
`t_i ∈ T_d ⟹ E_i = 0`
`t_i ∈ T_d ⟹ C_i = 0.5`
`t_i ∈ T_d ⟹ I_i = 0`
`t_i ∈ T_d ⟹ S_i = n`
`¬∃ t_i ∈ T_d : E_i ≠ 0 ∨ C_i ≠ 0.5 ∨ I_i ≠ 0 ∨ S_i ≠ n`
###...###.
