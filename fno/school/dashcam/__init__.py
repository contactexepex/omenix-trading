"""The write-once dashcam and its seals.

Story MS-P1c: one gz JSONL file per session, slot and kind saved once through O9's data store, its receipt pushed
before `seal` returns; seal checking, the public counts file and the replay reader."""
