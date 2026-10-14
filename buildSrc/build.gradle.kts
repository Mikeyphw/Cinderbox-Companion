plugins { `kotlin-dsl` }
repositories { google(); mavenCentral() }
# AGP API is needed to compile the visitor, but must not leak into root plugin resolution.
dependencies { compileOnly("com.android.tools.build:gradle:8.10.1") }
