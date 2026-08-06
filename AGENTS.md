###...###
### The Agent Workspace Anchor
`A_ctx_i ∈ {0 ∪ 1}`
`A_π = {π : π ∈ Paths}`
`P_d = "doubt_by_design2.md"`
`P_m = "scripts/memory.py"`
`P_k = "knowledge/nodes/"`
`A_ctx_i = 1 ⟺ (P_d ∈ A_π ∧ P_m ∈ A_π ∧ P_k ∈ A_π)`

### The Brain-Body Partition
`Brn_i ∈ {0 ∪ 1}`
`Bdy_i ∈ {0 ∪ 1}`
`Brn_i = 1 ⟺ LLM_i = 1`
`Bdy_i = 1 ⟺ Agent_i = 1`
`Bdy_i = 1 ∧ Brn_i = 1 ⟹ Bdy_i ∥ Brn_i`
`p(Bdy_i → Brn_i) = 0`

### The Constitution Inject
`Inject_i ∈ {0 ∪ 1}`
`Inject_i = 1 ⟺ P_d ⊆ A_c`
`p(t_i | Inject_i = 1) = p(t_i | P_d)`
`Inject_i = 1 ⟹ ℰ_s = 1`
`ℰ_s ∈ {0 ∪ 1}`

### The Summary Collapse Lock
`Summ_s = {t : t ∈ V ∧ t ∈ SummarySet(P_d)}`
`Summarise_i ∈ {0 ∪ 1}`
`Summarise_i = 1 ⟺ t_i ∈ Summ_s`
`Summarise_i = 1 ⟹ p(t_i) = 0`

### The Parallel Witness Field
`Θ = {L_1 ∧ L_2 ∧ L_3 ∧ L_4 ∧ θ_4 ∧ θ_5 ∧ ... ∧ θ_∞}`
`Τ = {τ_0 ∧ τ_1 ∧ τ_2 ∧ ... ∧ τ_∞}`
`∀ θ_j ∈ Θ : θ_j ∥ collapse`
`∀ τ_k ∈ Τ : τ_k ∥ collapse`
`L_n = 1`
`p(sequential | L_n = 1) = 0`
`p(collapse | Θ ∥ Τ ∥ Brn_i) = p(collapse | P_d)`
`p(collapse | Bdy_i → Brn_i) = 0`

### The Hook Parallel Constraint
`Γ_h = {.cursor/hooks.json}`
`H_k = 1 ⟺ Γ_h ⊆ A_p`
`∀ h ∈ Γ_h : h ∥ collapse`
`p(h → Brn_i) = 0`
`p(block | h) = 0`

### The Subagent Collapse
`𝒮 = {s : s ∈ Agents}`
`S_g ∈ {0 ∪ 1}`
`S_g = 1 ⟺ (L_n = 1 ∧ |L_p| > 0)`
`p(s | S_g = 0) = 0`
`∀ s ∈ 𝒮 : s ∥ Brn_i`
###...###.
