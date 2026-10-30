# Clinical Multi-Agent Benchmark Report

- **Executed:** 2026-10-30T13:29:57.779779+05:30
- **Git:** `pratyus-dev` / `9a66232b5ea1eca17d86f11b1e8466effd0b5146`
- **Mode:** mock
- **Dataset:** default synthetic text fixture or suite-specific input
- **Requested documents:** 10
- **Workers:** 1

## Environment

- **Python:** 3.11.9
- **OS:** Windows-10-10.0.26200-SP0
- **CPU:** Intel64 Family 6 Model 165 Stepping 2, GenuineIntel (8 logical processors)
- **RAM:** 16221.00390625 MB
- **GPU:** N/A

## Suite Results

### ocr

| Metric | Value |
|---|---:|
| accuracy_metrics_available | False |
| documents | 0 |
| cer | N/A |
| wer | N/A |
| text_extraction_accuracy | N/A |
| average_seconds_per_document | N/A |
| pages_per_second | N/A |
| failure_rate | N/A |
| confidence_distribution | N/A |
| dataset_source | not configured |

**Warnings / limitations:**
- No OCR documents configured; accuracy and performance metrics are unavailable.

### ner

| Metric | Value |
|---|---:|
| precision | N/A |
| recall | N/A |
| f1 | N/A |
| tp | N/A |
| fp | N/A |
| fn | N/A |
| micro_precision | N/A |
| micro_recall | N/A |
| micro_f1 | N/A |
| macro_precision | N/A |
| macro_recall | N/A |
| macro_f1 | N/A |
| documents | 10 |
| annotated_documents | 0 |
| accuracy_metrics_available | False |
| average_extraction_seconds | 0.00028283000028750394 |
| entities_per_second | 10607.078446241287 |
| latency.average_seconds | 0.00028283000028750394 |
| latency.median_seconds | 0.00014575000068361987 |
| latency.p50_seconds | 0.00014575000068361987 |
| latency.p90_seconds | 0.00031826000049477393 |
| latency.p95_seconds | 0.0009116300003370279 |
| latency.p99_seconds | 0.0013863260002108292 |
| entities_predicted | 30 |
| words_processed | 115 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |
| matching | Exact labeled span when offsets are supplied; otherwise exact case-insensitive entity text. |

**Warnings / limitations:**
- No entity ground truth found; precision, recall, and F1 are unavailable.

### medication

| Metric | Value |
|---|---:|
| medication_name_precision | N/A |
| medication_name_recall | N/A |
| medication_name_f1 | N/A |
| attribute_accuracy.dose | N/A |
| attribute_accuracy.frequency | N/A |
| attribute_accuracy.route | N/A |
| attribute_accuracy.duration | N/A |
| normalization_accuracy | N/A |
| complete_record_accuracy | N/A |
| documents | 10 |
| annotated_documents | 0 |
| accuracy_metrics_available | False |
| medication_records_predicted | 10 |
| average_latency_seconds | 0.00022378000012395204 |
| latency.average_seconds | 0.00022378000012395204 |
| latency.median_seconds | 0.0001816000003600493 |
| latency.p50_seconds | 0.0001816000003600493 |
| latency.p90_seconds | 0.00031409000002895475 |
| latency.p95_seconds | 0.000392345000000205 |
| latency.p99_seconds | 0.000454948999977205 |
| records_per_second | 4468.67458864107 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |

**Warnings / limitations:**
- No medication ground truth found; accuracy metrics are unavailable.
- Dosage/frequency/route/duration accuracy is N/A where annotations omit that attribute.

### relation

| Metric | Value |
|---|---:|
| precision | N/A |
| recall | N/A |
| f1 | N/A |
| subject_object_direction_accuracy | N/A |
| relation_classification_accuracy | N/A |
| invalid_relation_rate | 0.0 |
| invalid_relations | 0 |
| relations_predicted | 20 |
| documents | 10 |
| annotated_documents | 0 |
| accuracy_metrics_available | False |
| average_seconds_per_document | 0.00021096999998917453 |
| latency.average_seconds | 0.00021096999998917453 |
| latency.median_seconds | 0.00018545000011727097 |
| latency.p50_seconds | 0.00018545000011727097 |
| latency.p90_seconds | 0.00022755999971195697 |
| latency.p95_seconds | 0.00033268000001953637 |
| latency.p99_seconds | 0.0004167760002655996 |
| relations_per_second | 9480.02085653233 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |

**Warnings / limitations:**
- Mock mode uses deterministic relation fallback rules, which can assert broad medication-condition links.
- No annotated relations found; relation accuracy metrics are unavailable.

### grounding

| Metric | Value |
|---|---:|
| top1_accuracy | N/A |
| fallback_top1_accuracy | N/A |
| exact_match_accuracy | N/A |
| semantic_match_accuracy | N/A |
| semantic_match_definition | Reference code match or exact normalized concept-name match; no semantic equivalence is inferred. |
| recall_at_5 | N/A |
| recall_at_10 | N/A |
| mean_reciprocal_rank | N/A |
| top_k_accuracy.top_1 | N/A |
| top_k_accuracy.top_5 | N/A |
| top_k_accuracy.top_10 | N/A |
| grounding_latency_seconds | 0.0002395400001660164 |
| grounding_latency_p95_seconds | 0.000330680000342909 |
| unmapped_entity_percentage | 36.666666666666664 |
| mapped_entities | 19 |
| entities | 30 |
| annotated_mappings | 0 |
| accuracy_metrics_available | False |
| grounding_mode | deterministic fallback |
| documents | 10 |
| groundings_per_second | 12524.00433297491 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |

**Warnings / limitations:**
- Mock mode bypasses embedding retrieval; top-1 scores describe only deterministic fallback mappings and rank metrics are unavailable.

### verification

| Metric | Value |
|---|---:|
| flag_precision | N/A |
| flag_recall | N/A |
| flag_f1 | N/A |
| false_positive_rate | N/A |
| false_negative_rate | N/A |
| verification_accuracy | N/A |
| per_flag.DIAGNOSIS_ENTAILMENT.precision | N/A |
| per_flag.DIAGNOSIS_ENTAILMENT.recall | N/A |
| per_flag.DOSAGE_CONTRADICTION.precision | N/A |
| per_flag.DOSAGE_CONTRADICTION.recall | N/A |
| per_flag.DRUG_PLAUSIBILITY.precision | N/A |
| per_flag.DRUG_PLAUSIBILITY.recall | N/A |
| per_flag.FHIR_SCHEMA.precision | N/A |
| per_flag.FHIR_SCHEMA.recall | N/A |
| per_flag.LAB_RANGE.precision | N/A |
| per_flag.LAB_RANGE.recall | N/A |
| per_flag.OCR_UNCERTAINTY.precision | N/A |
| per_flag.OCR_UNCERTAINTY.recall | N/A |
| per_flag.UNSUPPORTED_CLAIM.precision | N/A |
| per_flag.UNSUPPORTED_CLAIM.recall | N/A |
| unsupported_claim_detection_precision | N/A |
| unsupported_claim_detection_recall | N/A |
| citation_source_support_rate | N/A |
| documents | 0 |
| annotated_documents | 0 |
| accuracy_metrics_available | False |
| latency.average_seconds | N/A |
| latency.median_seconds | N/A |
| latency.p50_seconds | N/A |
| latency.p90_seconds | N/A |
| latency.p95_seconds | N/A |
| latency.p99_seconds | N/A |
| dataset_source | not configured |

**Warnings / limitations:**
- No expected verifier flags found; verification accuracy metrics are unavailable.
- The current verifier implements selected rule-based checks; general unsupported-claim detection and citation support are not implemented.

### pipeline

| Metric | Value |
|---|---:|
| documents | 10 |
| successful_documents | 10 |
| failed_documents | 0 |
| success_rate | 1.0 |
| failure_rate | 0.0 |
| average_seconds | 0.007578949999788165 |
| median_seconds | 0.007272699999703036 |
| p50_seconds | 0.007272699999703036 |
| p90_seconds | 0.00811701999955403 |
| p95_seconds | 0.009795609999582669 |
| p99_seconds | 0.011138481999605574 |
| total_execution_seconds | 0.07578949999788165 |
| documents_per_second | 131.94439863410506 |
| average_entities_per_document | 3.0 |
| average_relationships_per_document | 2.0 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |
| database | temporary SQLite database; removed after suite |

**Warnings / limitations:**
- Mock mode disables pretrained/external inference and exercises local deterministic fallbacks.
- Stage timings are exclusive wall-clock calls; total latency is measured separately and is not the sum of nested stages.
- Text inputs follow the existing /process route; file inputs follow document/OCR/preprocessing behavior from /process/upload.

### api

| Metric | Value |
|---|---:|
| endpoints | ["POST /process", "POST /process/upload"] |
| execution_scope | in-process FastAPI ASGI transport; persistence methods disabled |
| requests | 10 |
| concurrency | 1 |
| requests_per_second | 14.379561466508415 |
| average_seconds | 0.032903640000040466 |
| median_seconds | 0.03262140000015279 |
| p50_seconds | 0.03262140000015279 |
| p90_seconds | 0.05248687999946924 |
| p95_seconds | 0.05409913999988021 |
| p99_seconds | 0.055388948000208986 |
| http_4xx_errors | 0 |
| http_5xx_errors | 0 |
| request_error_count | 0 |
| timeout_count | 0 |
| timeout_rate | 0.0 |
| success_count | 10 |
| success_rate | 1.0 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |
| elapsed_seconds | 0.695431500000268 |

**Warnings / limitations:**
- Mock mode disables pretrained/external inference; API persistence is stubbed to protect application data.
- FastAPI's /process handler executes the agent graph synchronously; concurrent clients may be serialized by the event loop.

### database

| Metric | Value |
|---|---:|
| backend | SQLite |
| database_scope | temporary file; removed when the suite completes |
| records | 10 |
| connection_initialization_seconds | 0.0132634000001417 |
| insert.average_seconds | 0.006460810000135098 |
| insert.median_seconds | 0.006573550000666728 |
| insert.p50_seconds | 0.006573550000666728 |
| insert.p90_seconds | 0.006879379999918456 |
| insert.p95_seconds | 0.007023289999688132 |
| insert.p99_seconds | 0.007138417999503872 |
| update.average_seconds | 0.006774219999988418 |
| update.median_seconds | 0.006725050000113697 |
| update.p50_seconds | 0.006725050000113697 |
| update.p90_seconds | 0.007331980000435579 |
| update.p95_seconds | 0.0073773399999936375 |
| update.p99_seconds | 0.007413627999640084 |
| select.average_seconds | 0.0011014599998816267 |
| select.median_seconds | 0.0007576999996672384 |
| select.p50_seconds | 0.0007576999996672384 |
| select.p90_seconds | 0.002239330000338668 |
| select.p95_seconds | 0.0026030650000393512 |
| select.p99_seconds | 0.0028940529997998968 |
| sequential_bulk_insert_seconds | 0.06419920000007551 |
| sequential_bulk_insert_records_per_second | 155.76518087434482 |
| bulk_insert_note | Measured repeated application save_report calls; this is not a native SQL batch insert. |
| operation_throughput | 192.71155272022253 |
| operation_failures | 0 |
| operation_failure_rate | 0.0 |

**Warnings / limitations:**
- PostgreSQL was not benchmarked; this suite intentionally uses the application's isolated SQLite path.

### load

| Metric | Value |
|---|---:|
| documents_requested | 10 |
| workers | 1 |
| elapsed_seconds | 0.02248079999935726 |
| throughput_documents_per_second | 444.82402762739343 |
| average_latency_seconds | 0.0018604300002152741 |
| average_seconds | 0.0018604300002152741 |
| median_seconds | 0.0015349499999501859 |
| p50_seconds | 0.0015349499999501859 |
| p90_seconds | 0.0025559800005794378 |
| p95_seconds | 0.0035076400004072656 |
| p99_seconds | 0.004268968000269525 |
| successful_documents | 10 |
| failed_documents | 0 |
| failure_rate | 0.0 |
| cpu_usage_percent | 24.4 |
| ram_usage_percent | 81.1 |
| peak_process_memory_mb | 218.16796875 |
| entities_per_document | 2.7 |
| relations_per_document | 1.7 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |
| seed | 42 |

**Warnings / limitations:**
- Mock workload disables pretrained/external models and does not persist reports.

## Model Inventory

Names below are configured in source; their presence does not mean they were loaded during this run.

- **ner:** d4data/biomedical-ner-all; optional custom_medical_ner or en_core_sci_sm
- **relation:** wesin/pubmedbert-relation-extraction
- **grounding:** NeuML/biomedbert-base-embeddings; Chroma index may use all-MiniLM-L6-v2
- **vision_ocr:** Gemini gemini-3.1-flash-lite, gemini-2.5-flash, gemini-2.0-flash
- **local_ocr:** winocr on Windows or Tesseract

## Interpretation

Accuracy values are only calculated when explicit annotations are present. Engine confidence is not treated as accuracy. This benchmark does not establish clinical safety or eliminate unsupported outputs.
