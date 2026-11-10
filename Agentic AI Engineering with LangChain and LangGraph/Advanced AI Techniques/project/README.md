# UDA-Hub – Autonomous Knowledge Agent



## Setup
```bash
pip install -r requirements.txt
python build_articles.py            # writes 15 articles to data/external/cultpass_articles.jsonl
# run notebook 01_external_db_setup.ipynb   (creates cultpass.db)
# run notebook 02_core_db_setup.ipynb       (loads the 15 articles into udahub.db)
python seed_test_data.py            # deterministic subscriptions/reservations for tests
```
Notebook 01 has a `TODO` cell for extra data – `seed_test_data.py` covers it.

## Run
```bash
python 03_agentic_app.py --user-id f556c0 --ticket-id t-001   # interactive chat as Bob
python 03_agentic_app.py --demo                               # scripted scenarios with routing/logging output
```
Or in the notebook: `chat_interface(orchestrator, "1", external_user_id="f556c0")`.

## Test
```bash
pytest tests/test_tools.py -q                      # no LLM needed
OPENAI_API_KEY=... pytest tests/test_scenarios.py -q   # resolve, escalate, blocked, memory scenarios
```
Test users: Bob `f556c0` (active premium), Cathy `88382b` (active basic), Eva `f1f10d` (cancelled), Alice `a4ab87` (blocked).

Design: `agentic/design/architecture.md`. Logs: `logs/agent_events.jsonl`.

python 04_inspect_state.py    # workflow-state inspection (get_state / get_state_history)

## Built With

* [LangGraph](www.langchain.com) 
* [LangChain](www.langchain.com) 
* [Item3](www.sqlite.org) 

Include all items used to build project.

## License
[License](../LICENSE.md)
