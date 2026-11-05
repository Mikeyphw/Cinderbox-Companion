package com.sdvsync.mods

import org.json.JSONArray
import org.json.JSONObject

/** Bounded, schema-checked DataStore representation. Corrupt data is never silently erased. */
object ModUpdateObservationCodec {
    private const val MAX_BYTES = 262144
    private const val MAX_OBSERVATIONS = 512

    fun encode(observations: Map<String, ModUpdateObservation>): String {
        require(observations.size <= MAX_OBSERVATIONS) { "Too many update observations" }
        val items = JSONArray()
        observations.toSortedMap().forEach { (key, observation) ->
            val id = ModUpdatePolicy.normalizedId(observation.uniqueID)
            require(key == id) { "Noncanonical observation key" }
            require(observation.installedVersion.length in 1..80) { "Invalid installed version" }
            val candidate = observation.candidateVersion
            if (candidate != null) ModUpdatePolicy.checkedCandidateVersion(candidate)
            require(ModUpdatePolicy.assess(observation.installedVersion, candidate) == observation.status) {
                "Contradictory remote status"
            }
            items.put(JSONObject().apply {
                put("id", id)
                put("installed", observation.installedVersion)
                put("candidate", candidate ?: JSONObject.NULL)
                put("status", observation.status.name)
            })
        }
        val serialized = JSONObject().apply {
            put("schema", 1)
            put("items", items)
        }.toString()
        require(serialized.toByteArray(Charsets.UTF_8).size <= MAX_BYTES) {
            "Update observation storage limit"
        }
        return serialized
    }

    fun decode(value: String): Map<String, ModUpdateObservation> {
        require(value.toByteArray(Charsets.UTF_8).size <= MAX_BYTES) { "Observation storage too large" }
        val root = JSONObject(value)
        val rootKeys = root.keys()
        while (rootKeys.hasNext()) require(rootKeys.next() in setOf("schema", "items"))
        require(root.getInt("schema") == 1) { "Unknown update observation schema" }
        val items = root.getJSONArray("items")
        require(items.length() <= MAX_OBSERVATIONS) { "Too many observations" }
        val result = linkedMapOf<String, ModUpdateObservation>()
        for (index in 0 until items.length()) {
            val row = items.getJSONObject(index)
            val keys = row.keys()
            while (keys.hasNext()) {
                require(keys.next() in setOf("id", "installed", "candidate", "status"))
            }
            val id = ModUpdatePolicy.normalizedId(row.getString("id"))
            val installed = row.getString("installed")
            require(installed.length in 1..80) { "Invalid version in storage" }
            val candidate = if (row.isNull("candidate")) null else row.getString("candidate")
            if (candidate != null) ModUpdatePolicy.checkedCandidateVersion(candidate)
            val status = UpdateAssessment.valueOf(row.getString("status"))
            require(status == ModUpdatePolicy.assess(installed, candidate)) {
                "Forged update classification"
            }
            require(result.put(id, ModUpdateObservation(id, installed, candidate, status)) == null) {
                "Duplicate update observation"
            }
        }
        return result
    }
}
