## Extension experiments (results_v2_ext + core reference arms)

Arms found: s1_peaceful/llm/e1_fastctx4b (N=10), s1_peaceful/llm/e1_gptoss (N=10), s1_peaceful/llm/e2_v2 (N=10), s1_peaceful/llm/e3_noauto (N=10), s1_peaceful/llm/e5_pl2 (N=5), s1_peaceful/llm/e5_pl4 (N=5), s1_peaceful/noop/e3_noauto (N=5), s1_peaceful/rule/e3_noauto (N=10), s1_peaceful/rule/e5_pl2 (N=5), s1_peaceful/rule/e5_pl4 (N=5), s3_daynight/llm/e1_fastctx4b (N=10), s3_daynight/llm/e1_gptoss (N=10), s3_daynight/llm/e2_v2 (N=10)

### E1 Multi-model

| Scenario | Model | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final cov.\ (\%) | BS | Ep.\ $\geq$80\,\% (\%) | Rejected (\%) | Invalid (\%) | Lat.\ med.\ (s) | Temporal $n$ (\%) | $\Delta$ (pp) | 95\,\% CI | $t$ (df) | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | Qwen3.8-27B (primary) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49.2 ± 10.6 | 18.1 ± 4.5 | 13.3 | 63.8 | 0.3 | 1.2 | 0 (0.0) | ref. |  |  |  |  |
| S1 Peaceful | FastContext-4B | 10 | 60.0 ± 5.2 | [57.0, 63.2] | 45.7 ± 8.9 | 19.1 ± 5.1 | 16.6 | 80.0 | 0.0 | 1.5 | 0 (0.0) | +2.2 | [-2.5, 6.9] | 0.95 (23.8) | 0.349 / 0.699 | +0.32 |
| S1 Peaceful | gpt-oss-120b | 10 | 50.2 ± 10.6 | [43.4, 56.0] | 35.6 ± 15.9 | 13.1 ± 6.2 | 13.8 | 67.0 | 0.0 | 1.1 | 0 (0.0) | -7.7 | [-15.7, 0.4] | -2.06 (13.1) | 0.060 / 0.200 | -0.89 |
| S1 Peaceful | rule (reference) | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 45.5 ± 10.1 | 20.4 ± 5.0 | 11.9 | 56.2 | 0.0 | 0.0 | n/a | +0.0 | [-4.4, 4.4] | 0.01 (37.8) | 0.995 / 0.995 | +0.00 |
| S3 Day/Night | Qwen3.8-27B (primary) | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 51.8 ± 8.6 | 18.3 ± 5.3 | 14.8 | 57.6 | 0.0 | 0.8 | 0 (0.0) | ref. |  |  |  |  |
| S3 Day/Night | FastContext-4B | 10 | 59.6 ± 6.8 | [55.7, 63.7] | 46.2 ± 10.0 | 17.3 ± 2.8 | 14.1 | 85.8 | 0.3 | 1.6 | 0 (0.0) | -1.7 | [-8.7, 5.3] | -0.51 (17.5) | 0.618 / 0.699 | -0.22 |
| S3 Day/Night | gpt-oss-120b | 10 | 52.0 ± 11.4 | [44.6, 57.8] | 38.3 ± 15.9 | 16.4 ± 6.0 | 12.1 | 67.9 | 0.0 | 1.2 | 0 (0.0) | -9.3 | [-18.6, 0.0] | -2.12 (16.2) | 0.050 / 0.200 | -0.91 |
| S3 Day/Night | rule (reference) | 10 | 57.0 ± 4.1 | [54.7, 59.4] | 42.7 ± 7.2 | 20.2 ± 3.3 | 14.1 | 60.1 | 0.0 | 0.0 | n/a | -4.3 | [-10.5, 1.8] | -1.53 (13.4) | 0.150 / 0.150 | -0.65 |

*Rows `rule (reference)' repeat the core rule arm for orientation; their $p$ is not part of the Holm family.*

### E2 Prompt variant

| Scenario | Prompt | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final cov.\ (\%) | BS | Ep.\ $\geq$80\,\% (\%) | Rejected (\%) | Invalid (\%) | Lat.\ med.\ (s) | Temporal $n$ (\%) | $\Delta$ (pp) | 95\,\% CI | $t$ (df) | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | v1 (core) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49.2 ± 10.6 | 18.1 ± 4.5 | 13.3 | 63.8 | 0.3 | 1.2 | 0 (0.0) | ref. |  |  |  |  |
| S1 Peaceful | v2 + history 5 | 10 | 59.1 ± 3.8 | [57.0, 61.4] | 47.9 ± 7.2 | 18.2 ± 3.7 | 15.2 | 58.8 | 0.0 | 1.0 | 14 (4.8) | +1.2 | [-2.9, 5.3] | 0.61 (27.7) | 0.546 / 0.661 | +0.19 |
| S3 Day/Night | v1 (core) | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 51.8 ± 8.6 | 18.3 ± 5.3 | 14.8 | 57.6 | 0.0 | 0.8 | 0 (0.0) | ref. |  |  |  |  |
| S3 Day/Night | v2 + history 5 | 10 | 58.4 ± 4.3 | [56.0, 61.0] | 52.5 ± 6.7 | 17.4 ± 3.8 | 12.1 | 61.9 | 0.0 | 1.1 | 13 (4.5) | -2.9 | [-9.1, 3.3] | -1.01 (13.7) | 0.331 / 0.661 | -0.43 |

### E3 Autonomous layer

| Autonomy | Agent | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final cov.\ (\%) | BS | Ep.\ $\geq$80\,\% (\%) | Rejected (\%) | Marginal vs no-op (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ | On $-$ off (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| autonomy on | LLM-full | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49.2 ± 10.6 | 18.1 ± 4.5 | 13.3 | 63.8 | -1.6 | [-6.4, 3.2] | 0.491 / 1.000 | -0.24 |  |  |  |
| autonomy on | rule | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 45.5 ± 10.1 | 20.4 ± 5.0 | 11.9 | 56.2 | -1.6 | [-6.2, 3.0] | 0.481 / 1.000 | -0.25 |  |  |  |
| autonomy on | noop | 10 | 59.5 ± 5.3 | [56.1, 62.3] | 46.4 ± 11.8 | 16.6 ± 3.9 | 12.4 | n/a | ref. |  |  |  |  |  |  |
| autonomy off | LLM-full | 10 | 26.8 ± 6.3 | [22.9, 30.2] | 14.4 ± 7.2 | 5.5 ± 2.7 | 11.0 | 65.7 | +6.3 | [0.4, 12.3] | 0.039 / 0.156 | +1.05 | +31.1 | [25.8, 36.4] | <0.001 / <0.001 |
| autonomy off | rule | 10 | 20.3 ± 7.2 | [16.2, 24.6] | -2.6 ± 10.1 | 2.0 ± 0.0 | 10.7 | 96.1 | -0.2 | [-6.6, 6.2] | 0.950 / 1.000 | -0.03 | +37.6 | [31.9, 43.4] | <0.001 / <0.001 |
| autonomy off | noop | 5 | 20.4 ± 4.2 | [17.3, 23.7] | 2.8 ± 5.2 | 1.0 ± 0.0 | 11.0 | n/a | ref. |  |  |  | +39.1 | [33.5, 44.6] | <0.001 / <0.001 |

*The no-op on-vs-off row measures the autonomous layer alone; its $p$ is reported but not Holm-adjusted (it is not one of the six planned tests).*

### E5 Path-loss sensitivity

| $n$ | Agent | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final cov.\ (\%) | BS | Ep.\ $\geq$80\,\% (\%) | Rejected (\%) | LLM $-$ rule (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ | vs $n$=3.0 (pp) | 95\,\% CI | $p$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | LLM-full | 5 | 61.1 ± 4.4 | [57.9, 64.7] | 56.6 ± 5.1 | 19.2 ± 3.4 | 17.2 | 56.7 | -0.6 | [-7.0, 5.7] | 0.820 / 1.000 | -0.13 | +3.2 | [-2.4, 8.8] | 0.235 |
| 2.0 | rule | 5 | 61.7 ± 4.4 | [58.6, 65.1] | 47.2 ± 9.6 | 24.4 ± 4.7 | 13.1 | 54.7 |  |  |  |  | +3.8 | [-1.7, 9.3] | 0.151 |
| 3.0 (core) | LLM-full | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49.2 ± 10.6 | 18.1 ± 4.5 | 13.3 | 63.8 | -0.0 | [-4.4, 4.4] | 0.995 / 1.000 | -0.00 | ref. |  |  |
| 3.0 (core) | rule | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 45.5 ± 10.1 | 20.4 ± 5.0 | 11.9 | 56.2 |  |  |  |  | ref. |  |  |
| 4.0 | LLM-full | 5 | 58.8 ± 8.5 | [51.2, 63.4] | 48.2 ± 15.6 | 18.2 ± 4.7 | 13.1 | 60.0 | -2.5 | [-12.9, 7.9] | 0.577 / 1.000 | -0.34 | +0.9 | [-9.4, 11.2] | 0.837 |
| 4.0 | rule | 5 | 61.2 ± 4.1 | [58.0, 64.5] | 51.4 ± 4.7 | 22.2 ± 2.6 | 13.8 | 57.9 |  |  |  |  | +3.4 | [-1.9, 8.6] | 0.186 |

### Inventory

| Experiment | Scenario | Agent | Model | Prompt | Autonomy | $n$ | Valid $N$ |
|---|---|---|---|---|---|---|---|
| E1 | S1 Peaceful | LLM-full | FastContext-4B | v1 | on | 3.0 | 10 |
| E1 | S3 Day/Night | LLM-full | FastContext-4B | v1 | on | 3.0 | 10 |
| E1 | S1 Peaceful | LLM-full | gpt-oss-120b | v1 | on | 3.0 | 10 |
| E1 | S3 Day/Night | LLM-full | gpt-oss-120b | v1 | on | 3.0 | 10 |
| E2 | S1 Peaceful | LLM-full | Qwen3.8-27B | v2+hist 5 | on | 3.0 | 10 |
| E2 | S3 Day/Night | LLM-full | Qwen3.8-27B | v2+hist 5 | on | 3.0 | 10 |
| E3 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | off | 3.0 | 10 |
| E3 | S1 Peaceful | rule | - | - | off | 3.0 | 10 |
| E3 | S1 Peaceful | noop | - | - | off | 3.0 | 5 |
| E5 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | on | 2.0 | 5 |
| E5 | S1 Peaceful | rule | - | - | on | 2.0 | 5 |
| E5 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | on | 4.0 | 5 |
| E5 | S1 Peaceful | rule | - | - | on | 4.0 | 5 |
