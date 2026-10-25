"""The receipts as one run's step sees them (story MS-P1j, judge 523): looked up on `main` as the run fetched it before
the step, never fetched again, and never committed here. Every git call it makes only reads, so the step's thread can
run beside the run's own git writer; the receipts its writes add are committed by the run's single counts commit."""

from ...storage.receipt_publisher import PushedReceipt, RemoteReceipts


class RunReceipts:
    """A `ReceiptPublisher` for a step whose receipts the run's counts commit takes."""

    def __init__(self, remote: RemoteReceipts):
        self.remote = remote

    def refresh(self) -> None:
        """On the run's own thread, once, before the step's work."""
        self.remote.refresh()

    def published(self, drive_path: str) -> PushedReceipt | None:
        return self.remote.find(drive_path)

    def publish(self, drive_path: str, what: str) -> PushedReceipt | None:
        """Nothing is committed or pushed here: the receipt file the data store wrote waits for the run's counts
        commit, so there is no commit to name yet (None) unless an earlier run already pushed it."""
        return self.remote.find(drive_path)
