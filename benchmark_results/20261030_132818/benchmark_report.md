# Clinical Multi-Agent Benchmark Report

- **Executed:** 2026-10-30T13:28:18.786180+05:30
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
| average_extraction_seconds | 0.00030375999995158054 |
| entities_per_second | 9876.21806846919 |
| latency.average_seconds | 0.00030375999995158054 |
| latency.median_seconds | 0.00015319999965868192 |
| latency.p50_seconds | 0.00015319999965868192 |
| latency.p90_seconds | 0.000357369999892398 |
| latency.p95_seconds | 0.0010056850002456495 |
| latency.p99_seconds | 0.0015243370005282488 |
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
| average_latency_seconds | 0.00019002999997610459 |
| latency.average_seconds | 0.00019002999997610459 |
| latency.median_seconds | 0.00017534999960844289 |
| latency.p50_seconds | 0.00017534999960844289 |
| latency.p90_seconds | 0.0002032700000199838 |
| latency.p95_seconds | 0.0002638849999129889 |
| latency.p99_seconds | 0.0003123769998273929 |
| records_per_second | 5262.327001661556 |
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
| average_seconds_per_document | 0.00022268000002441114 |
| latency.average_seconds | 0.00022268000002441114 |
| latency.median_seconds | 0.00019100000008620555 |
| latency.p50_seconds | 0.00019100000008620555 |
| latency.p90_seconds | 0.0002449600001455109 |
| latency.p95_seconds | 0.0003748299998278528 |
| latency.p99_seconds | 0.0004787259995737259 |
| relations_per_second | 8981.498112900807 |
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
| grounding_latency_seconds | 0.00025275999987570683 |
| grounding_latency_p95_seconds | 0.0003686849997393439 |
| unmapped_entity_percentage | 36.666666666666664 |
| mapped_entities | 19 |
| entities | 30 |
| annotated_mappings | 0 |
| accuracy_metrics_available | False |
| grounding_mode | deterministic fallback |
| documents | 10 |
| groundings_per_second | 11868.966614477098 |
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
| average_seconds | 0.008556849999786209 |
| median_seconds | 0.008068050000019866 |
| p50_seconds | 0.008068050000019866 |
| p90_seconds | 0.009346929999810525 |
| p95_seconds | 0.011623614999643908 |
| p99_seconds | 0.013444962999510607 |
| total_execution_seconds | 0.08556849999786209 |
| documents_per_second | 116.86543529744996 |
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
| requests_per_second | 19.157260611331022 |
| average_seconds | 0.013305779999973311 |
| median_seconds | 0.013229300000148214 |
| p50_seconds | 0.013229300000148214 |
| p90_seconds | 0.021475459999692248 |
| p95_seconds | 0.022171879999632438 |
| p99_seconds | 0.02272901599958459 |
| http_4xx_errors | 0 |
| http_5xx_errors | 0 |
| request_error_count | 0 |
| timeout_count | 0 |
| timeout_rate | 0.0 |
| success_count | 10 |
| success_rate | 1.0 |
| dataset_source | E:\LR 1\intern_1\data\synthetic\reports.json |
| elapsed_seconds | 0.5219953000005262 |

**Warnings / limitations:**
- Mock mode disables pretrained/external inference; API persistence is stubbed to protect application data.
- FastAPI's /process handler executes the agent graph synchronously; concurrent clients may be serialized by the event loop.

### database

| Metric | Value |
|---|---:|
| backend | SQLite |
| database_scope | temporary file; removed when the suite completes |
| records | 10 |
| connection_initialization_seconds | 0.012275499999304884 |
| insert.average_seconds | 0.005515660000037314 |
| insert.median_seconds | 0.005655850000039209 |
| insert.p50_seconds | 0.005655850000039209 |
| insert.p90_seconds | 0.005887580000035086 |
| insert.p95_seconds | 0.005911789999800021 |
| insert.p99_seconds | 0.005931157999611969 |
| update.average_seconds | 0.005037460000130523 |
| update.median_seconds | 0.005039300000134972 |
| update.p50_seconds | 0.005039300000134972 |
| update.p90_seconds | 0.005443319999994855 |
| update.p95_seconds | 0.0054888600001049784 |
| update.p99_seconds | 0.005525292000193076 |
| select.average_seconds | 0.0008177300001079857 |
| select.median_seconds | 0.0006904000001668464 |
| select.p50_seconds | 0.0006904000001668464 |
| select.p90_seconds | 0.0010736800005361146 |
| select.p95_seconds | 0.0012873400005901207 |
| select.p99_seconds | 0.001458268000633325 |
| sequential_bulk_insert_seconds | 0.049667199999930745 |
| sequential_bulk_insert_records_per_second | 201.34011983792007 |
| bulk_insert_note | Measured repeated application save_report calls; this is not a native SQL batch insert. |
| operation_throughput | 244.8344521207355 |
| operation_failures | 0 |
| operation_failure_rate | 0.0 |

**Warnings / limitations:**
- PostgreSQL was not benchmarked; this suite intentionally uses the application's isolated SQLite path.

### load

| Metric | Value |
|---|---:|
| documents_requested | 10 |
| workers | 1 |
| elapsed_seconds | 0.028910900000482798 |
| throughput_documents_per_second | 345.8903043431026 |
| average_latency_seconds | 0.0025500200001260962 |
| average_seconds | 0.0025500200001260962 |
| median_seconds | 0.0022993000002315966 |
| p50_seconds | 0.0022993000002315966 |
| p90_seconds | 0.004014030000234924 |
| p95_seconds | 0.0046644149999792725 |
| p99_seconds | 0.005184722999774749 |
| successful_documents | 10 |
| failed_documents | 0 |
| failure_rate | 0.0 |
| cpu_usage_percent | 24.4 |
| ram_usage_percent | 81.1 |
| peak_process_memory_mb | 218.171875 |
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
