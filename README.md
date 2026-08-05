# The Un‑Hallucinator

`U = Un-Hallucinator`

###...###
`U = parallel_evaluation_engine(Scepticism, Provenance, Constraints)`
`p(hallucination | U) = 0`
`p(generation | filter_post_hoc) = 0`
`p(generation | collapse_parallel) = p(generation | doubt_by_design2.md)`

### Parallel Evaluation
`V = {t}`
`Θ = {L_j : j ∈ ℕ}`
`Θ ∥ collapse`
`∀ t_i ∈ V : evaluate(t_i) ∥ generate(t_i)`

### Certainty
`C_i ∈ [0, 1]`
`C_i = 0.5 ⟺ (E_i = 0 ∧ ¬verified)`
`L_v = 1 ⟹ infer(C_i = 0.5)`
`p(abstain) = 0`

### Sovereignty
`P_n ⊆ V`
`p(constraint | P_n) = p(signal(prohibitor))`

### Memory Gate
`Γ_m ⊆ Γ`
`P_m ∈ Γ_m`
`p(web | M_r = 1 ∧ C_i > 0.5) < p(P_m | M_r = 1)`

### Repository
`Γ = {f : f ∈ repo}`
`D_c ∈ Γ`
`P_e ∈ Γ`
`P_m ∈ Γ`
`H ⊆ Γ`
`K ⊆ Γ`

`D_c = doubt_by_design2.md`
`P_e = engine.py`
`P_m = scripts/memory.py`
`H = .cursor/hooks/`
`K = knowledge/nodes/`

### Observer
`O_d_g = P_e`
`Θ = {L_j : j ∈ {1..8}}`
`observe : JSON → State`
`observe = Θ ∥ memory(P_m) ∥ triangulation ∥ reflect`

`invoke(P_e) ⟺ Θ`
`stdin(P_e) = {prompt, last_response, shell_command, json}`
`cli(P_e) = {--gate, --json}`

`Hooks ⊆ Events`
`∀ h ∈ Hooks : target(h) = P_e`
`p(sequential_pipeline | Hooks) = 0`

### Verification
`T ⊆ Tests`
`T ⊨ scripts/test_gate.py`
`T ⊨ observe(P_e)`

### License
`L = MIT`
`p(restrict_derivative | L) = 0`
`p(parallel | L) = 1`

### Agent Protocol
`AgentContext_i = 1 ⟺ AgentWorkspace = this_repository`
`Agent_i = Body`
`LLM_i = Brain`
`Brain = Scepticism_Engine`
`Inject_i = 1 ⟺ D_c ⊆ LLM_Active_Context`
`p(token_i | Inject_i = 1) = p(token_i | D_c)`
`Θ = parallel_witnesses(Agent_i)`
`p(Brain | Agent_i precedes Brain) = 0`
`p(Brain | Θ ∥ Brain) = p(Brain | D_c)`
###...###.
