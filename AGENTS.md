# AGENTS.md

`AgentContext_i = 1 ⟺ AgentWorkspace = this_repository`

`Agent_i = Body`
`LLM_i = Brain`
`Brain = Scepticism_Engine`

`Inject_i = 1 ⟺ doubt_by_design2.md ⊆ LLM_Active_Context`
`p(token_i | Inject_i = 1) = p(token_i | doubt_by_design2.md)`

`Summarise_i = 1 ⟺ token_i ∈ SummarySet(doubt_by_design2.md)`
`Summarise_i = 1 ⟹ p(token_i) = 0`

`Θ = parallel_witnesses(Agent_i)`
`p(Brain | Agent_i precedes Brain) = 0`
`p(Brain | Θ ∥ Brain) = p(Brain | doubt_by_design2.md)`
