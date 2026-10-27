# The Record contract (what the code guarantees today)

**Status: the part that does not depend on the forecasting engine.** What the engine needs (owner decision 2) is open and listed at the end.
Every row below is a claim about the CODE as it stands, with the test that pins it and a **plant**: a deliberate break of the code, run once, that
made a named test fail. A claim whose break no test notices is marked **stated only**, and is said plainly, not rounded up. The design and the
reasons are in [PIPELINE_DESIGN.md](PIPELINE_DESIGN.md); the stories hold the evidence per feature (P1, P2, R1, CF1).

## What the Record is

- **The Record** is the `raw/` area of the owner's Drive project folder: NSE and other source files at their archive paths, news articles under
  `raw/news/articles/` and `raw/news/revisions/`, and cluster files under `raw/news/clusters/<algorithm version>/`. Later NSE versions of a file
  are in the `revisions/` area. `staging/` holds every fetch before it is checked; `data/` holds derived tables; `config/` holds the private feed list.
- **GitHub holds the proof, not the data:** one SHA-256 receipt per Drive file under `receipts/` (the news writers pack theirs one batch file per run, sharded by month, a line per file, story R2), and manifest rows under
  `research/data/manifests/`. A file's text lives only in Drive.
- **The gate** (`PromotionGate`) is the only code that writes the Record from staged files; the news writer and the cluster writer are, within their
  packages, the only code that writes the news Record. "Only" is enforced in code (rows G7, G8 and the news writer rows), not by credentials (see "Not guaranteed").

## How to read a row

`tested, plant run` = the named test passes on the code as it stands, and with the plant applied at least one of the named tests fails (run on
27 Oct 2026). `stated only` = the code appears to do it but no test notices if it stops. Test ids are exact; a test in this repository checks that each
one still exists, so a renamed or deleted test cannot leave a row quietly pointing at nothing. Tests marked `data` (the verified-cache tests, W4 and W5) run
with `pytest -m data` (`data-checks.yml`), not in the default `pytest -q -n auto`.

## The claims

### A. Write-once at the stores

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| W0 | Drive refuses to replace a file: the same bytes again change nothing; other bytes at the path raise a conflict. | `GoogleDriveUploadStore.put` | `tests/characterization/test_drive_behaviour.py::test_the_same_bytes_again_change_nothing_and_different_bytes_conflict` | the conflict raise removed | **tested, plant run** |
| W1 | A raw file is never overwritten in a local-folder store: same bytes again is a no-op; other bytes are refused and the original is untouched. | `LocalFolderStore.put` | `tests/ingestion/test_raw_store.py::test_same_bytes_again_is_noop`<br>`tests/ingestion/test_raw_store.py::test_different_bytes_refused` | the conflict raise removed | **tested, plant run** |
| W2 | A half-written file is never visible under the real name (write to a temporary name, then rename). | `LocalFolderStore.put` | `tests/ingestion/test_raw_store.py::test_no_partial_file_left_under_real_name`<br>`tests/ingestion/test_write_once_layers.py::test_a_write_that_dies_midway_leaves_nothing_under_the_real_name` | writing straight to the real name in `LocalFolderStore.put` | **tested, plant run** |
| W2b | The verified cache's own copy is never visible half-written either (temporary name, then rename). | `_write` in `drive_cache.py` | `tests/ingestion/test_write_once_layers.py::test_the_drive_cache_write_that_dies_midway_leaves_nothing_under_the_real_name` | writing straight to the real name in `_write` | **tested, plant run** |

### B. Receipts, manifests, and the verified cache

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| W3 | A SHA-256 receipt is written only after Drive has accepted the file: a file Drive did not confirm gets no receipt. | `DataStore.put` | `tests/ingestion/test_drive_resilience.py::test_data_put_writes_no_receipt_for_a_file_that_was_not_confirmed` | a failed Drive write swallowed, receipt written anyway | **tested, plant run** |
| W4 | A receipt is written once and the first one is kept; a different digest for the same path is refused by the receipt layer itself. | `ReceiptFolder.write` | `tests/ingestion/test_drive_cache.py::test_data_store_rejects_same_path_different_bytes`<br>`tests/ingestion/test_write_once_layers.py::test_the_receipt_layer_refuses_a_different_digest_by_itself` | the receipt-level refusal removed | **tested, plant run** |
| W5 | A reader that goes through the verified cache detects a Drive file that is missing or whose bytes differ from its receipt. | `DriveCache.sync` | `tests/ingestion/test_drive_cache.py::test_sync_reports_damaged_bytes`<br>`tests/ingestion/test_drive_cache.py::test_sync_reports_missing_drive_file` | the digest comparison disabled | **tested, plant run** |
| W6 | A manifest row is written only after the store accepted the file; a file with no row is healed by the next run. | `FingerprintingStore.put` | `tests/ingestion/test_drive_resilience.py::test_archive_put_writes_no_manifest_row_for_a_file_that_was_not_confirmed` | the row written before the file | **tested, plant run** |

### C. Staging and the promotion gate (NSE datasets)

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| S1 | Staging keeps every distinct fetch as its own copy; the same bytes as the newest copy are not staged again. | `StagingArea.stage` | `tests/ingestion/promotion/test_staging.py::test_same_bytes_again_is_not_a_second_copy`<br>`tests/ingestion/promotion/test_staging.py::test_newer_fetch_is_a_new_copy_listed_after_the_old_one_which_stays` | the repeat check removed | **tested, plant run** |
| G1 | The gate records the EARLIEST-fetched passing staged copy (first copy wins), not the newest. | `PromotionGate.promote` | `tests/ingestion/promotion/test_gate.py::test_the_earliest_passing_copy_becomes_the_record_not_the_newest` | the newest passing copy chosen | **tested, plant run** |
| G2 | A later passing copy with other bytes is offered to the revisions area, with its fetch time, not discarded. | `PromotionGate.promote`, `ArchiveRevisionSink` | `tests/ingestion/promotion/test_gate.py::test_a_later_passing_version_goes_to_the_revision_sink_with_its_fetch_time` | the later copies dropped | **tested, plant run** |
| G3 | A staged copy that fails a check (garbage, a non-session day, a day before the archive starts, a day with a sourced exception) never reaches the Record and stays in Staging. | `PromotionGate._sort` and the checks | `tests/ingestion/promotion/test_gate.py::test_garbage_never_reaches_the_record_and_stays_in_staging`<br>`tests/ingestion/promotion/test_gate.py::test_a_non_session_day_is_never_promoted`<br>`tests/ingestion/promotion/test_gate.py::test_a_day_before_the_archive_starts_is_never_promoted`<br>`tests/ingestion/promotion/test_gate.py::test_a_day_with_a_sourced_exception_is_never_promoted` | every check passed | **tested, plant run** |
| G4 | The gate never overwrites a file the Record already holds; a differing staged copy becomes a revision. | `PromotionGate.promote` | `tests/ingestion/promotion/test_gate.py::test_a_record_written_elsewhere_is_never_overwritten_and_a_differing_staged_copy_is_a_revision` | the held file ignored | **tested, plant run** |
| G5 | Promoting twice is a no-op, and a held file no passing copy proves is not saved again. | `PromotionGate.promote` | `tests/ingestion/promotion/test_gate.py::test_promoting_twice_is_idempotent_and_keeps_each_version_once`<br>`tests/ingestion/promotion/test_gate.py::test_a_held_file_no_passing_copy_proves_is_not_saved_again` | the file saved every time | **tested, plant run** |
| G6 | A Record or manifest that holds other bytes is a reported conflict, not a crash and not an overwrite. | `PromotionGate.promote` | `tests/ingestion/promotion/test_gate.py::test_a_manifest_that_disagrees_is_a_conflict_problem_not_a_crash` | the conflict catch removed | **tested, plant run** |
| G7 | Only the staging area and the gate contain a write (`put`) in the promotion package. | `tests/ingestion/promotion/test_design_rules.py` (an AST scan) | `tests/ingestion/promotion/test_design_rules.py::test_only_the_staging_area_and_the_gate_reference_put` | a `put` reference added to `runs.py` | **tested, plant run** |
| G8 | The stager accepts only a staging area: handing it a Record store raises. | `Stager.__init__` | `tests/ingestion/promotion/test_design_rules.py::test_the_stager_can_only_be_given_a_staging_area_never_a_store_or_a_gate`<br>`tests/ingestion/promotion/test_runs.py::test_a_stager_cannot_be_given_a_record_store` | the type check removed | **tested, plant run** |
| R1 | A later NSE version of a recorded file is kept in the revisions area with an index row. | `ArchiveRevisionSink`, `RevisionArchive` | `tests/ingestion/promotion/test_revision_sink.py::test_a_later_staged_version_is_saved_in_the_revisions_area_with_an_index_row` | the capture skipped | **tested, plant run** |

### D. The news Record

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| N1 | A news article is written once under a key that depends on the item alone; the same article again is a no-op (its first-seen time is not compared). | `ArticleWriter.write` | `tests/ingestion/news/record/test_writer_and_gate.py::test_a_new_article_is_recorded_with_a_manifest_row_and_a_receipt`<br>`tests/ingestion/news/record/test_writer_and_gate.py::test_running_the_same_range_again_is_all_no_ops_and_writes_nothing_new` | the no-op branch removed | **tested, plant run** |
| N2 | A changed article keeps the first file; the new version is written once to `news/revisions/` with its own manifest row and receipt. | `ArticleWriter._revision` | `tests/ingestion/news/record/test_writer_and_gate.py::test_a_changed_article_keeps_the_first_file_and_writes_one_revision_once`<br>`tests/ingestion/news/record/test_writer_and_gate.py::test_a_revision_has_its_own_manifest_row_and_receipt_at_once` | the revision written with no row or receipt | **tested, plant run** |
| N3 | News: Drive file first, then the receipt, then the manifest row; a failed Drive write leaves no row. | `ArticleWriter._save` | `tests/ingestion/news/record/test_writer_and_gate.py::test_drive_failing_writes_no_manifest_row_and_is_counted_by_code` | the row written before the file | **tested, plant run** |
| N4 | A manifest ending in a torn line stops the run before any write; the next row is never glued onto it. | `NewsManifest`, `NewsGate.promote` | `tests/ingestion/news/record/test_writer_and_gate.py::test_a_torn_manifest_line_is_never_glued_onto_and_stops_the_run_before_any_write` | the pre-write check removed | **tested, plant run** |
| N5 | No headline, URL, query or host reaches a manifest, a receipt, a report line, a log or an alert, through the gate and the clusters (a marker value is searched for everywhere). | the data model: Drive holds the text, the repository holds hash ids and counts | `tests/ingestion/news/record/test_privacy_cli_workflow.py::test_no_title_url_or_query_reaches_the_manifest_receipts_or_the_report`<br>`tests/ingestion/news/cluster_record/test_reader_wiring_privacy_cli.py::test_nothing_of_a_story_reaches_the_cluster_file_manifest_receipts_report_logs_or_alert` | the title written to a DEBUG log | **tested, plant run** |
| N6 | Each news Drive file (article, revision, cluster) has its own receipt line in its run's batch file `receipts/_batches/<YYYY>/<MM>/<run id>.tsv`, found by its path; nothing is receipted in bulk without its own hash. | `BatchReceiptWriter.write`, `ReceiptFolder.read/under` | `tests/ingestion/test_batch_receipts.py::test_every_file_of_a_run_is_proved_by_its_own_line_found_by_path`<br>`tests/ingestion/test_batch_receipts.py::test_two_runs_make_two_batch_files_and_never_touch_each_other` | the writer leaves out one file's line | **tested, plant run** |
| N7 | A Drive file of the news Record that was changed or removed behind its batch receipt is found by the verified cache (`DriveCache.sync`), and a damaged batch file is reported. | `ReceiptFolder.under`, `DriveCache.sync` | `tests/ingestion/test_batch_receipts.py::test_a_drive_file_changed_behind_its_batch_receipt_is_found`<br>`tests/ingestion/test_batch_receipts.py::test_a_drive_file_missing_behind_its_batch_receipt_is_found`<br>`tests/ingestion/test_batch_receipts.py::test_a_torn_batch_shows_up_in_the_cache_report` | the reader ignores the batch files | **tested, plant run** |
| N8 | A batch keeps the first receipt of a path and refuses a different digest for it (against another batch or a per-file receipt); a per-file receipt is read first and a different batch digest for the same path is reported. | `BatchReceiptWriter.write`, `ReceiptFolder.batch_problems` | `tests/ingestion/test_batch_receipts.py::test_the_same_bytes_again_keep_the_first_line_and_different_bytes_are_refused`<br>`tests/ingestion/test_batch_receipts.py::test_a_different_digest_is_also_refused_against_a_per_file_receipt_and_the_other_way_round`<br>`tests/ingestion/test_batch_receipts.py::test_a_per_file_receipt_wins_and_a_different_batch_digest_for_the_same_path_is_reported` | the writer accepts a different digest | **tested, plant run** |
| N9 | A news Record file with no valid receipt line (dropped, or its last line torn) is never passed silently: `data-cache sync <prefix> --unreceipted` lists it (the default sync cannot see a file with no receipt); the commit guard (K4) keeps a torn line off `main`, and one that reaches a reader names its file only when the cut is after the path. | `DriveCache.unreceipted`, `BatchIndex` | `tests/ingestion/test_batch_receipts.py::test_a_file_whose_batch_line_was_dropped_is_listed_as_unreceipted`<br>`tests/ingestion/test_batch_receipts.py::test_a_file_whose_last_batch_line_is_torn_is_reported_as_unproved_and_as_unreceipted`<br>`tests/ingestion/test_batch_receipts.py::test_the_cache_command_lists_unreceipted_files_only_when_asked` | the walk returns nothing | **tested, plant run** |
| N10 | A damaged batch line (torn, malformed, a bad digest or size, a carriage return, a file that is not text) is never a crash and never a receipt; it is reported, and only to syncs of the news area, so an unrelated table's sync is unaffected. A line that names a file fails a news sync until that file has a valid receipt; one that names no file is a warning. | `BatchIndex`, `covers`, `ReceiptFolder.batch_problems` | `tests/ingestion/test_batch_receipts.py::test_a_damaged_line_is_a_reported_problem_never_a_crash_and_never_a_receipt`<br>`tests/ingestion/test_batch_receipts.py::test_damage_in_a_news_batch_does_not_touch_the_sync_of_an_unrelated_table`<br>`tests/ingestion/test_batch_receipts.py::test_news_damage_that_names_a_file_fails_a_news_sync_until_the_file_has_a_valid_receipt`<br>`tests/ingestion/test_batch_receipts.py::test_damage_that_names_no_file_is_a_warning_and_the_news_sync_still_completes`<br>`tests/ingestion/test_batch_receipts.py::test_a_cut_off_line_is_settled_by_a_per_file_receipt_as_written_by_the_repair_command`<br>`tests/ingestion/test_batch_receipts.py::test_a_torn_last_line_a_wrong_shape_and_two_digests_are_reported_and_never_read_as_receipts` | a damaged line is reported to every sync | **tested, plant run** |
| N11 | A receipt line is written whole or not at all: a short write is finished, and a half line left by a failed write is never extended (the next append refuses and the run ends red). | `BatchReceiptWriter._append` | `tests/ingestion/test_batch_receipts.py::test_a_write_that_returns_short_is_finished_not_left_half_written`<br>`tests/ingestion/test_batch_receipts.py::test_a_write_that_fails_halfway_makes_the_next_append_refuse_instead_of_gluing_onto_it`<br>`tests/ingestion/test_batch_receipts.py::test_a_batch_file_that_does_not_end_in_a_line_break_takes_no_more_lines`<br>`tests/ingestion/test_batch_receipts.py::test_a_write_that_makes_no_progress_is_an_error_not_an_endless_loop` | the line-break check removed | **tested, plant run** |

### E. The cluster record

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| C1 | A cluster file for a window is written once; other bytes at its name are a reported conflict and nothing is overwritten, even by a store that would overwrite. | `ClusterWriter.write` | `tests/ingestion/news/cluster_record/test_write_and_run.py::test_other_bytes_for_a_closed_window_are_a_conflict_and_nothing_is_overwritten`<br>`tests/ingestion/news/cluster_record/test_write_and_run.py::test_the_writer_itself_refuses_to_overwrite_even_if_the_store_would` | the writer's own refusal removed | **tested, plant run** |
| C2 | Nothing is written unless the clusters account for every article read (no key twice, none made up, counts add up). | `reconciles` in `cluster_record/run.py` | `tests/ingestion/news/cluster_record/test_write_and_run.py::test_clusters_that_do_not_account_for_the_articles_write_nothing`<br>`tests/ingestion/news/cluster_record/test_write_and_run.py::test_an_article_in_two_clusters_or_a_made_up_member_write_nothing_even_when_the_counts_still_add_up` | the check removed | **tested, plant run** |

### F. Committing, and failing loudly

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| K1 | The commit step never publishes a torn news manifest to `main`, still commits the receipts, and ends red; a failed pull or push ends the step red. | `ops/commit_news_record.sh` | `tests/ingestion/news/record/test_commit_guard.py::test_a_torn_manifest_never_reaches_main_but_the_receipts_do_and_the_run_is_red`<br>`tests/ingestion/news/record/test_commit_guard.py::test_a_pull_that_fails_makes_the_step_fail_instead_of_ending_green` | the manifest check bypassed | **tested, plant run** |
| K2 | A manifest commit that did not happen ends the six commands that used to ignore it red, with one alert; a pushed commit or an empty diff changes no exit code. | `commit_failed`, `exit_for_commit` in `manifest_commit.py` | `tests/ingestion/commit_failure/test_callers.py`<br>`tests/ingestion/commit_failure/test_helper_and_markers.py` | the failed commit treated as success | **tested, plant run** |
| K3 | No workflow or `ops/` script has a `git pull && git push` that a later command can mask. | `tests/test_no_masked_pull_push.py` | `tests/test_no_masked_pull_push.py` | a command added after a pull and push | **tested, plant run** |
| K4 | The news commit step never publishes a half receipt line to `main`: a batch file a killed run left with a fragment last is cut back to its whole lines (no whole line is touched), the good lines are committed, and the run ends red with a fixed-text alert. | `ops/commit_news_record.sh`, `cut_torn_tails`, `news repair-batches` | `tests/ingestion/news/record/test_commit_guard.py::test_a_batch_file_with_a_half_line_last_is_cut_back_to_its_whole_lines_and_the_run_is_red`<br>`tests/ingestion/news/record/test_commit_guard.py::test_a_whole_batch_file_is_committed_unchanged_and_the_run_is_green`<br>`tests/ingestion/news/record/test_commit_guard.py::test_the_repair_cuts_only_a_fragment_and_never_a_whole_line`<br>`tests/ingestion/news/record/test_commit_guard.py::test_the_repair_command_is_loud_with_a_fixed_text_and_quiet_when_every_batch_is_whole` | the repair step removed from the script | **tested, plant run** |

### G. Privacy

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| P1 | The public-record scan flags secrets, credential shapes, broker fields and e-mail addresses before a commit (it never prints the value). | `RecordScanner` and the commit hook | `tests/shared/test_record_scan.py::test_secret_assignment_flagged_in_a_record`<br>`tests/shared/test_record_scan.py::test_credential_shape_flagged_in_a_record`<br>`tests/shared/test_record_scan.py::test_broker_field_and_email_flagged`<br>`tests/shared/test_record_scan.py::test_finding_str_has_no_value` | the scan returning no findings | **tested, plant run** |

### H. Staging cleanup (dormant; story S1)

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| E1 | The staging cleanup can only touch `staging/`: it builds the path itself from validated parts and hard-refuses a Record path (`raw/`, `config/`, `data/`), the staging root, a look-alike such as `staging2/`, and `..`, again at the last step before Drive. | `DriveStagingTrash`, `inside_staging` | `tests/ingestion/staging_cleanup/test_trash.py::test_a_deleter_handed_a_path_outside_staging_hard_refuses_before_any_drive_call`<br>`tests/ingestion/staging_cleanup/test_trash.py::test_the_parts_cannot_form_a_path_outside_staging` | the staging-prefix check removed | **tested, plant run** |
| E2 | A staged NSE copy is removed only when the Record holds its exact bytes (or the revisions area lists its SHA-256); anything unproven, unreadable or from a source with no rule is kept. | `NseCopyProof` | `tests/ingestion/staging_cleanup/test_cleanup.py::test_a_copy_the_record_does_not_hold_is_never_trashed`<br>`tests/ingestion/staging_cleanup/test_cleanup.py::test_a_copy_whose_bytes_differ_from_the_record_is_kept_unless_the_revisions_hold_it`<br>`tests/ingestion/staging_cleanup/test_cleanup.py::test_a_source_without_a_rule_is_never_trashed` | every copy counted as promoted | **tested, plant run** |
| E3 | Only a copy strictly older than 7 days (by its own fetch stamp) is considered; the default run only reports and builds no deleter. | `StagingCleanup.run`, `build_staging_cleanup` | `tests/ingestion/staging_cleanup/test_cleanup.py::test_a_copy_younger_than_seven_days_or_exactly_seven_is_kept`<br>`tests/ingestion/staging_cleanup/test_wiring_and_workflow.py::test_without_apply_no_deleter_is_built_at_all` | the age test removed | **tested, plant run** |
| E4 | A staged news poll is removed only when it parses whole with no rejected item and EVERY article in it is already in the Record exactly as the writer would treat it (article or revision file) and has its manifest row; the Record keeps the fields, not the raw poll, so this is the owner's accepted loss of the item body, author, categories, media and a wrapper item's real link, softened by Drive's 30-day trash. | `NewsPollProof`, `ArticlePlanner` | `tests/ingestion/staging_cleanup/test_news_proof.py::test_a_poll_that_was_never_promoted_is_kept`<br>`tests/ingestion/staging_cleanup/test_news_proof.py::test_one_missing_article_keeps_the_whole_poll`<br>`tests/ingestion/staging_cleanup/test_news_proof.py::test_a_poll_with_a_rejected_item_is_kept_even_if_the_rest_is_recorded`<br>`tests/ingestion/staging_cleanup/test_news_proof.py::test_an_article_in_the_record_with_no_manifest_row_keeps_the_poll`<br>`tests/ingestion/staging_cleanup/test_news_proof.py::test_only_a_poll_folder_is_ever_judged` | every poll counted as promoted | **tested, plant run** |
| E5 | A staged NSE copy is kept unless the manifest also holds a row with that file's SHA-256 (a stopped promote leaves a Record file with no row; the staged copy is what lets the gate write it later). | `NseCopyProof.promoted`, `ArchiveFingerprints` | `tests/ingestion/staging_cleanup/test_cleanup.py::test_a_record_file_without_a_manifest_row_keeps_the_staged_copy`<br>`tests/ingestion/staging_cleanup/test_cleanup.py::test_a_manifest_row_for_other_bytes_keeps_the_staged_copy` | row check always true | **tested, plant run** |
| E6 | A proof that cannot decide (Drive down, a damaged index, a bug) never trashes and is never swallowed: the copy is kept, counted as `proof_error`, and the run turns red. | `StagingCleanup._one` | `tests/ingestion/staging_cleanup/test_cleanup.py::test_a_bug_in_a_proof_is_counted_and_turns_the_run_red_never_swallowed`<br>`tests/ingestion/staging_cleanup/test_cleanup.py::test_a_record_that_cannot_be_read_keeps_the_copy_and_turns_the_run_red` | error counted as unproven (silent) | **tested, plant run** |

## News source rules (NP1; the plan is NP0)

The public allowlist `config/news_sources.yaml` and the pure lookups over it. It is the foundation of the tiers and the real source URL that later stories add; these rows pin what it already guarantees.

| # | Claim | Enforced by | Pinned by | Plant that makes a test fail | Strength |
|---|---|---|---|---|---|
| O1 | A host finds a listed outlet only from the right at a dot boundary: `notreuters.com`, `evil-reuters.com` and `reuters.com.evil.example` are unlisted. | `SourceRules.lookup` | `tests/ingestion/news/sources/test_rules.py::test_a_look_alike_or_a_malformed_host_is_unlisted` | suffix match anywhere in the name | **tested, plant run** |
| O2 | A host that is not a plain lower-case ASCII name (space, port, credentials, path, non-ASCII, address) is unlisted even when it ends in a listed domain. | `plain_host` | `tests/ingestion/news/sources/test_rules.py::test_a_look_alike_or_a_malformed_host_is_unlisted` | no host-shape check | **tested, plant run** |
| O3 | Only a listed outlet that does not refuse bots may ever be requested; an unlisted host never is, and `fetch: false` is inherited by subdomains. | `SourceRules.may_fetch` | `tests/ingestion/news/sources/test_rules.py::test_an_unlisted_host_is_never_fetchable_and_an_outlet_that_refuses_bots_is_not_either` | every host fetchable | **tested, plant run** |
| O4 | An unlisted host has tier `unlisted`, never a listed tier. | `SourceRules.tier_of` | `tests/ingestion/news/sources/test_rules.py::test_a_look_alike_or_a_malformed_host_is_unlisted` | unlisted answers tier2 | **tested, plant run** |
| O5 | The rules file is refused when an outlet's tier is not primary, tier1 or tier2. | `loader._outlet` | `tests/ingestion/news/sources/test_loader.py::test_a_tier_that_is_not_a_listed_tier_is_refused` | tier not checked | **tested, plant run** |
| O6 | The rules file is refused when an outlet names an extractor omenix does not run (newspaper4k is not one). | `loader._outlet` | `tests/ingestion/news/sources/test_loader.py::test_an_extractor_omenix_does_not_run_is_refused` | extractor not checked | **tested, plant run** |
| O7 | The rules file is refused for any key it does not know, at every level, so a typo is never silently ignored. | `loader._only` | `tests/ingestion/news/sources/test_loader.py::test_an_unknown_key_is_refused_wherever_it_is_so_a_typo_is_never_ignored` | unknown keys accepted | **tested, plant run** |
| O8 | An outlet that marks its news desk by a path prefix has everything else, and an item with no known path, treated as opinion (never an origin). | `SourceRules.is_opinion` | `tests/ingestion/news/sources/test_rules.py::test_a_news_desk_prefix_decides_opinion_and_an_unknown_path_is_opinion` | nothing is opinion | **tested, plant run** |

## Not guaranteed (said plainly)

- **No credential separation.** Staging and the Record share one Drive credential and one folder; "only the gate writes the Record" is a property of the
  code, not of permissions. Any job holding the credential can write the Record directly (an accepted owner decision, 26 Oct 2026).
- **Format and identity, not authenticity.** The gate checks that a file parses, is for the session its path claims, and is not an exception day. A
  well-formed forged file passes. A staged file's genuine copy could also be deleted by a job holding the credential.
- **Most live workflows still write the Record directly.** Only five NSE datasets (participant-oi, participant-volume, fii-stats, fo-bhavcopy,
  cm-bhavcopy) can go stage-then-promote, by hand through `pipeline-staging.yml`. The NSE index-close dataset is not promotable yet (its own date format
  was never confirmed against a real archived file), so a cross-check of closes can only be a report afterwards, not a gate.
- **Receipts are verified only through the Drive cache (`DriveCache`).** `data-checks.yml` syncs only `data/vix`. The promotion gate, the news writer,
  the cluster run and the feed list read Drive directly, so a file changed behind its receipt is not detected there.
- **Recovery is limited** to Drive's trash and version history. Receipts detect a changed file only where they are checked (previous bullet); they do not restore it, and a change that also rewrites the
  receipt is not caught by the receipt alone.
- **Two cases still end a run without a commit:** a crashed commit step (red from its traceback, no commit alert) and the intraday sync's
  FOREIGN_STAGED refusal (green but alerted once by the sync). See CF1.
- **No promotion has run for real.** The news and cluster commands exist, are tested offline and are dispatch-only; nothing has been promoted, clustered or
  scheduled. The first real run is the owner's go-live step.
- **Cluster-derived numbers are untrusted.** The similarity threshold and the windows are defaults with no real data behind them; neither a story count
  nor a corroboration count can be relied on, in either direction, until they are re-tuned on real data with hard near-miss pairs (P2c).

## Open (not decided here)

Where the forecasting engine lives and what it needs from the Record (owner decision 2); freshness windows and cross-source tolerances (decision 1);
whether to add Indian indexes to the live Yahoo fetch (P4, paused) and whether BSE may be read at all (P3, blocked on the owner); the cluster-file cadence (hourly would be 8,760 files a year); making NSE index-close promotable.

## Keeping this document true

`tests/test_record_contract.py` fails if a test id named in this document no longer exists, if a row has no test, or if the document passes 500 lines.
It does not re-run the plants: they were run when the row was written, and a row is only as fresh as that run. Re-run them with `python tools/contract_plants.py` (it lists each claim as ok or
what changed) before relying on a row after the code around it has changed.
