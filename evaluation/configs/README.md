# configs

One file per model arm, plus `judge.json`. These are the 20 arms in the paper's leaderboard (Table 1).

- A config pins the provider, model id, sampling settings and token limit, so a run is reproducible from the config alone. Reasoning effort is a run argument (`--effort`, `medium` in the paper).
- API keys are never stored here. The provider layer (`src/openai_compat.py`, `src/llm_client.py`) reads them from the standard environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `ZAI_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `AZURE_API_KEY`.
- `price_per_mtok` (USD per million tokens) is optional and is used only for cost reporting.
- `base_url` pins an OpenAI-compatible endpoint (a local server, a gateway). Without it the provider's default endpoint is used.

`judge.json` fixes the LLM judge for the whole benchmark (`gpt-5.6-luna`). Every arm must be scored by the same judge for scores to be comparable. Override per run with `ADHERENCE_JUDGE_MODEL` / `ADHERENCE_JUDGE_PROVIDER` / `ADHERENCE_JUDGE_BASE_URL`, but results under a different judge are not comparable with the leaderboard.

To add your own model, copy the closest config, change `arm_id` and `model`, and run it with `--model <arm_id>`:

```json
{
  "arm_id": "my-model",
  "provider": "openai",
  "model": "my-org/my-model",
  "base_url": "http://localhost:8000/v1",
  "max_tokens": 16000
}
```
