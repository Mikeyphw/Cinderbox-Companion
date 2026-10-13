package com.sdvsync.util

import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream

/** Caps decompression *after* inflation: ZIP metadata can lie about entry sizes. */
class ZipBudget(
    private val maxEntries: Int,
    private val maxEntryBytes: Long,
    private val maxTotalBytes: Long
) {
    private var entries = 0
    private var totalBytes = 0L

    fun nextEntry() {
        entries++
        if (entries > maxEntries) throw SecurityException("Archive has too many entries")
    }

    fun copyEntry(input: InputStream, output: OutputStream, maxBytes: Long = maxEntryBytes) {
        var entryBytes = 0L
        val buf = ByteArray(32 * 1024)
        while (true) {
            val n = input.read(buf)
            if (n == -1) break
            entryBytes += n
            totalBytes += n
            if (entryBytes > maxBytes || totalBytes > maxTotalBytes) {
                throw SecurityException("Archive extraction limit exceeded")
            }
            output.write(buf, 0, n)
        }
    }

    fun readEntry(input: InputStream, maxBytes: Long = maxEntryBytes): ByteArray {
        val out = ByteArrayOutputStream()
        copyEntry(input, out, maxBytes)
        return out.toByteArray()
    }
}
