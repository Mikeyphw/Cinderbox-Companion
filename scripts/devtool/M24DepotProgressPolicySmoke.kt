package com.sdvsync.download

/** Run as main in a standalone Kotlin compiler without Android dependencies. */
fun main() {
  check(M24DepotProgressPolicy.displayedDepotPercent(0f, 54_600_000L) == null)
  check(M24DepotProgressPolicy.displayedDepotPercent(0f, 0L) == null)
  check(M24DepotProgressPolicy.displayedDepotPercent(Float.NaN, 10L) == null)
  check(M24DepotProgressPolicy.displayedDepotPercent(0.5f, 10L) == 50)
  check(M24DepotProgressPolicy.displayedDepotPercent(1f, 10L) == 100)
  check(M24DepotProgressPolicy.displayedDepotPercent(0.00001f, 10L) == 1)
  println("PASS_M24_DEPOT_PROGRESS_POLICY_6")
}
