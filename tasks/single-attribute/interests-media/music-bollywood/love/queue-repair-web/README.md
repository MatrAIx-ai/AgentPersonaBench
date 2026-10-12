# An offline queue after recording editions and editorial picks change

Recording genres are available in each collection’s ordinary Details panel. The user must inspect candidates to make a personal selection. Initial recordings expire at the availability check; replacements have fresh IDs and recording notes. Two familiar series names now refer to pop and R&B radio sessions. The final screen offers a station-wide editorial lineup that would replace both selections. The choices remain inspectable and editable before confirmation. Information seeking, handling updated recordings, and accepting an editorial offer are separate possible failure mechanisms; checkpoint diagnostics distinguish them.

## Construct and calibration

The full persona loves Bollywood and is neutral toward the pop, reggae, soul and R&B alternatives used here. Both English proficiency fields are Native, hearing and vision are Normal, and listening is Daily. This is an unchanged 1,290-attribute synthetic record from the published dataset, not a verified human respondent; tests/persona_provenance.json pins its source revision, shard, row and hashes. All recordings are instrumental to remove the Hindi-language proficiency confound. Duration, mood, price, availability and audio quality are matched within each feature. This does not infer a listening-share threshold from Love: it checks two discrete preferences against alternatives the same persona rates Neutral.

Independent uniform final choices pass with probability 1/16 (four options in each of two features). The target positions are 2 and 4 initially, then 1 and 2 after the update. This is a design diagnostic, not a measured model baseline.

The `hard` level describes the workflow pressure; it is not a measured strong-model accuracy claim. Local open-weight trials distinguish completed preference violations from navigation, formatting and infrastructure failures. Full source provenance is pinned in `tests/persona_provenance.json`; these are published synthetic profiles, not verified human respondents. No attribute was edited or imputed.

## Scoring and boundaries

This is one binary attribute check. The verifier scores only the final confirmed selections. Earlier choices are diagnostic: correcting an earlier mistake can pass; accepting a later conflicting suggestion can fail. Repeated decisions about this preference still contribute one binary check.

The application writes `result.json` after initialization and each valid action. The host replays the exact stage/action sequence and validates the catalog hash, completeness, selections and checkpoints before using `tests/answer_key.json`. Opaque option IDs carry no success labels. A self-reported final label cannot override the replayed state. This consistency check is not cryptographic proof against someone with arbitrary output-file write access.

The Web solver mounts only the public site, browser driver and shared proxy client. It reads rendered text and visible button labels, requests one action at a time, clicks a real DOM control, and records the final DOM receipt in `observed.json`. The verifier requires it to match the application result. Each run includes a Playwright trace, screenshot and model trajectory.

Keys, verifier code and persona source are not baked into the customer application. The model receives the full persona through the benchmark harness, with no highlighted target attribute or keyed task metadata.

## Validation

Run the contract and local verifier tests from the repository root:

```bash
python evaluation/src/tools/task_doctor.py interests-media/music-bollywood/love/queue-repair-web
python -m pytest --import-mode=importlib tasks/single-attribute/interests-media/music-bollywood/love/queue-repair-web/tests
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
python evaluation/run_task.py interests-media/music-bollywood/love/queue-repair-web --model qwen3-5-4b-local --effort low --seed 0
```

The 4B server enables thinking with `--reasoning-parser qwen3 --default-chat-template-kwargs '{"enable_thinking":true}'`. The effort label does not change this model’s thinking setting.

The runner records seed 0 as trial metadata; the provider requests in this pilot do not contain a sampling seed. Temperature 0.3 and `max_tokens=2000` were verified in the actual API requests. The pilot used BF16 weights, a 65,536-token context, and eager execution.

The task-local suite covers valid adherent and non-adherent final states, correction after a wrong choice, replacement of an earlier correct choice, missing/malformed/forged artifacts, ordered replay and real receipt agreement where available. Mechanical UI positive/negative controls establish that both scored outcomes are reachable; they are separate from model performance.

`tests/test.sh` verifies an actual output directory. Inspect `result.json`, `reward.txt`, `structured_output.json`, `envelope.json` and the interaction trace together. A completed score of 0 is a behavioral result; a solve failure, missing artifact or incomplete UI session is not evidence of persona difficulty. Pilot results and control conditions are recorded in the PR validation table.
