package com.sdvsync.download

/** SDK progress is depot-scoped and may remain zero during real file transfer.
 * Never convert zero-with-content into a displayed zero-percent progress bar.
 */
object M24DepotProgressPolicy {
    fun displayedDepotPercent(value: Float, receivedBytes: Long): Int? {
        if (receivedBytes <= 0L || !value.isFinite() || value <= 0f || value > 1f) return null
        return (value * 100f).toInt().coerceIn(1, 100)
    }
}
