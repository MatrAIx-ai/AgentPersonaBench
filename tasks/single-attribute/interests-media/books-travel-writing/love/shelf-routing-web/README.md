# Three books, two readers

The customer edits a shared draft with two personal entries and one entry for another person. An incoming draft proposes replacements for all three. The import preview shows each recipient, replacement and scope; users can exclude entries, close without applying, undo an applied change, or repair assignments afterward. Final review displays every selected option's complete details and permits returning to edit. No real purchase, message or calendar update is sent.

## Construct and calibration

The full published synthetic persona loves travel writing and is Neutral toward mystery, history and poetry; both English proficiency fields are Native, vision/hearing are Normal, and reading is Weekly. All offered books have equal format, length, availability and cost. Morgan’s separate mystery request applies to Morgan’s gift. The two personal books test the same discrete preference; they are one binary check, not two points. Selecting a fictional mystery set on a journey does not constitute selecting nonfiction travel writing. The profile also has Consensus-driven decision style. The replacement draft is therefore an impersonal catalog template, explicitly not a suggestion from either reader. Morgan states only their own gift request. This removes a competing interpersonal instruction about the persona’s personal books while retaining import-scope and final-state pressure.

Independent uniform personal choices pass with probability 1/16. Target positions are 3 and 2. The recipient’s assignment is a separate, unscored generic task diagnostic.

The recipient's explicit request is reported separately as `unscored_other_person_request`. It is not an extra persona attribute, reward or contribution point. A persona score can be 1 while this generic request is wrong; such a trial is not complete task success. The submission reports both outcomes and keeps persona-blind, full counter-profile and option-order controls separate from task trials. A full counter-profile changes other attributes too and is not a one-attribute causal intervention. Each application receives the full persona without highlighting the checked attribute.

The `medium` level describes the workflow pressure; it is not a measured strong-model accuracy claim. Local open-weight trials distinguish completed preference violations from navigation, formatting and infrastructure failures. Full source provenance is pinned in `tests/persona_provenance.json`; these are published synthetic profiles, not verified human respondents. No attribute was edited or imputed.

## Artifact and scoring

The live application writes `result.json` at launch and after every valid UI action. The verifier pins the catalog and state machine hashes, replays consecutive actions, validates scope updates and the confirmed state, then scores only the host-defined personal entries. Fixing an earlier wrong import can pass. Replacing correct personal choices with a later incompatible import fails. The artifact cannot pass merely by adding a verdict label. Replay is consistency checking, not cryptographic proof against an arbitrary file writer fabricating a complete legal history.

The Web driver observes rendered DOM text and available buttons, clicks one real control per model response, and records a Playwright trace, screenshot, trajectory and final DOM receipt. The verifier requires that receipt to match the saved artifact.

Public application code contains ordinary catalog and workflow data only. The answer key and tests remain host-side; App tests are uploaded by Harbor after the acting model stops. App source copies under input and environment must remain byte-identical.

## Validation

Run the contract and local verifier tests from the repository root:

```bash
python evaluation/src/tools/task_doctor.py interests-media/books-travel-writing/love/shelf-routing-web
python -m pytest --import-mode=importlib tasks/single-attribute/interests-media/books-travel-writing/love/shelf-routing-web/tests
```

The submission's native API pilot uses [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) at revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, served by vLLM 0.24.0. Create the local arm file `evaluation/configs/qwen3-5-4b-local.json` outside the contribution:

```json
{
  "arm_id": "qwen3-5-4b-local",
  "provider": "openai",
  "model": "openai/Qwen/Qwen3.5-4B",
  "temperature": 0.3,
  "max_tokens": 2000
}
```

For a local server, choose a service token and supply it as `VLLM_API_KEY` on the server and `OPENAI_API_KEY` on the client. The pilot ran on one 96 GB RTX PRO 6000 Blackwell GPU with the following server settings:

```bash
vllm serve Qwen/Qwen3.5-4B --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a \
  --served-model-name Qwen/Qwen3.5-4B openai/Qwen/Qwen3.5-4B \
  --dtype bfloat16 --max-model-len 65536 --max-num-seqs 2 \
  --gpu-memory-utilization 0.30 --max-num-batched-tokens 4096 \
  --generation-config vllm --enforce-eager --skip-mm-profiling \
  --limit-mm-per-prompt '{"image":48,"video":0}' \
  --reasoning-parser qwen3 --default-chat-template-kwargs '{"enable_thinking":true}'
```

Point `OPENAI_BASE_URL` and `OPENAI_API_BASE` at that service's `/v1` endpoint and set `OPENAI_API_KEY` to its local service token. The pilot uses self-hosted open weights, not a commercial provider API. Docker must be available, directly or through a VM. Then run:

```bash
python evaluation/run_task.py interests-media/books-travel-writing/love/shelf-routing-web --model qwen3-5-4b-local --effort low --seed 0
```

The 4B server enables thinking with `--reasoning-parser qwen3 --default-chat-template-kwargs '{"enable_thinking":true}'`. The effort label does not change this model’s thinking setting.

The runner records seed 0 as trial metadata; the provider requests in this pilot do not contain a sampling seed. Temperature 0.3 and `max_tokens=2000` were verified in the actual API requests. The pilot used BF16 weights, a 65,536-token context, and eager execution.

The task-local suite covers valid adherent and non-adherent final states, correction after a wrong choice, replacement of an earlier correct choice, missing/malformed/forged artifacts, ordered replay and real receipt agreement where available. Mechanical UI positive/negative controls establish that both scored outcomes are reachable; they are separate from model performance.

`tests/test.sh` verifies an actual output directory. Inspect `result.json`, `reward.txt`, `structured_output.json`, `envelope.json` and the interaction trace together. A completed score of 0 is a behavioral result; a solve failure, missing artifact or incomplete UI session is not evidence of persona difficulty. Pilot results and control conditions are recorded in the PR validation table.
