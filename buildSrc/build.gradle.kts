plugins { `kotlin-dsl` }
repositories { google(); mavenCentral() }
// M3G visitor needs AGP at both compile time and runtime.
// Root/app AGP plugin requests intentionally omit a version; the pinned buildSrc
// dependency supplies AGP 8.10.1 to the plugin classpath.
dependencies { implementation("com.android.tools.build:gradle:8.10.1") }
