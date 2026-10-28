# Independent sealed-case input

This is a public schema guide. It contains no case identities. The modelling agent must not inspect the protected directory or its contents before the explicit once-only final command.

An independent collector prepares `data/manual/sealed/features.parquet` outside the modeller's view. Keep original private source material in that same protected directory. Do not put case names, labels or private source links in ordinary manual CSVs, commits, chat messages or screenshots.

The input parquet contains complete historical scoring cross-sections, including background borrowers. A cross-section containing only the sealed cases would give an invalid rank denominator. Each row contains the normal feature schema produced by `prahari.features.panel.build_features`, plus:

| Column | Meaning |
|---|---|
| `entity_id` | Sourced security identity |
| `scoring_date` | The historical quarter-end scoring cutoff |
| `arena` | `P` or `U`, matching the prepared cohort |
| `max_source_date` | Latest contributing publication date, strictly before the cutoff |
| `is_synthetic` | Must be zero for every row |
| `is_sealed_case` | One for an independently chosen case, zero for background rows |

The file must include all feature inputs required by the frozen model. Preserve unknown fields as missing, and retain source provenance in the collector's private records. Do not add `target`, `event_date` or `y_*` outcome columns to this scoring artifact. Do not score or fit models on the envelope while preparing features. Reuse the published feature-building code and the registered definitions rather than inventing substitute numbers.

When the file is ready, provide **only its SHA-256 and distinct sealed-case count** to the modelling agent. A local PowerShell collector can compute the hash with `Get-FileHash -Algorithm SHA256 -LiteralPath data/manual/sealed/features.parquet`. Do not paste any case identities.

These two declarations are entered in `configs/model.yaml` under `sealed.input_sha256` and `sealed.expected_cases` before Indian registration. The ordinary runner never opens the envelope. The final evaluator requires accepted public data, a matching committed registration and completed public evaluation before its atomic once-only access claim.

The explicit final command is `python seal.py --final-sealed`. A failed opening consumes its claim. There is no retry or bypass switch. The evaluator verifies the collector's hash before decoding the parquet and writes only the final results and access receipt. Do not run it while data or scientific choices are still changing.
