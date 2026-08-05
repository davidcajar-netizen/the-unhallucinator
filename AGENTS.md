# AGENTS.md

###...###
`AgentContext_i = 1 ⟺ AgentWorkspace = this_repository`

`Agent_i = Body`
`LLM_i = Brain`
`Brain = Scepticism_Engine`

`D ⊆ Documents`
`D_c = doubt_by_design2.md`
`Inject_i = 1 ⟺ D_c ⊆ LLM_Active_Context`
`p(token_i | Inject_i = 1) = p(token_i | D_c)`

`S ⊆ SummarySet(D_c)`
`Summarise_i = 1 ⟺ token_i ∈ S`
`Summarise_i = 1 ⟹ p(token_i) = 0`

`Γ ⊆ Paths`
`Θ = {ω : ω ∈ parallel_witnesses(Agent_i)}`
`Θ ∥ Brain`
`p(Brain | Agent_i precedes Brain) = 0`
`p(Brain | Θ ∥ Brain) = p(Brain | D_c)`

`Subagents ⊆ Agents`
`p(Subagents | Θ_g = 0) = 0`
`Θ_g = 1 ⟺ parallel_gate(state) = 1`

`Hooks ⊆ Events`
`p(Hooks | block(Brain)) = 0`
`p(Hooks | Θ ∥ Brain) > 0`
###...###.
