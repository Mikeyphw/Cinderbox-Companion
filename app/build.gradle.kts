import java.util.Properties
import com.android.build.api.instrumentation.InstrumentationScope
import com.sdvsync.build.AndroidSafeMachineIdVisitorFactory

plugins {
    id("com.android.application")
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.sdvsync"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sdvsync"
        minSdk = 26
        targetSdk = 35
        versionCode = 14
        versionName = "0.1.1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // M16: CI must opt in explicitly; local development retains Android's debug key.
    // Never reuse release-signing secrets or permit a silent CI debug-key fallback.
    val requireStableDebugSigner =
        System.getenv("CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING") == "true"
    if (requireStableDebugSigner) {
        require(System.getenv("CINDERBOX_DEBUG_KEYSTORE_PATH")?.isNotBlank() == true)
        require(System.getenv("CINDERBOX_DEBUG_STORE_PASSWORD")?.isNotBlank() == true)
        require(System.getenv("CINDERBOX_DEBUG_KEY_PASSWORD")?.isNotBlank() == true)
        require(file(System.getenv("CINDERBOX_DEBUG_KEYSTORE_PATH")).isFile)
    }

    signingConfigs {
        if (requireStableDebugSigner) {
            create("ciDebug") {
                storeFile = file(System.getenv("CINDERBOX_DEBUG_KEYSTORE_PATH"))
                storeType = "PKCS12"
                storePassword = System.getenv("CINDERBOX_DEBUG_STORE_PASSWORD")
                keyAlias = "androiddebugkey"
                keyPassword = System.getenv("CINDERBOX_DEBUG_KEY_PASSWORD")
            }
        }
        val localProps = Properties()
        rootProject.file("local.properties").takeIf { it.exists() }?.inputStream()?.use {
            localProps.load(it)
        }
        create("release") {
            storeFile = file("${rootProject.projectDir}/keystore.jks")
            storePassword =
                localProps.getProperty("STORE_PASSWORD") ?: System.getenv("STORE_PASSWORD")
            keyAlias = "cinderbox"
            keyPassword = localProps.getProperty("KEY_PASSWORD") ?: System.getenv("KEY_PASSWORD")
        }
    }

    buildTypes {
        getByName("debug") {
            if (requireStableDebugSigner) {
                signingConfig = signingConfigs.getByName("ciDebug")
            }
        }
        release {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_11) } }

    buildFeatures {
        compose = true
        aidl = true
        buildConfig = true
    }

    androidResources { noCompress += "zip" }

    applicationVariants.all {
        outputs.all {
            (this as com.android.build.gradle.internal.api.BaseVariantOutputImpl).outputFileName =
                "CinderboxCompanion-v$versionName.apk"
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            // BouncyCastle/SpongyCastle packaging conflicts
            excludes += "META-INF/BCKEY.DSA"
            excludes += "META-INF/BCKEY.SF"
        }
        jniLibs { useLegacyPackaging = true }
    }
}

// Rewrite JavaSteam 1.8.0 HardwareUtils.getMachineID(), not the ROM or dependency cache.
// Apply to ALL compiled classes including external dependency jars.
androidComponents {
    onVariants(selector().all()) { variant ->
        variant.instrumentation.transformClassesWith(
            AndroidSafeMachineIdVisitorFactory::class.java,
            InstrumentationScope.ALL
        ) { }
    }
}

dependencies {
    // AndroidX
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.security.crypto)
    implementation(libs.androidx.documentfile)

    // Compose
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    debugImplementation(libs.androidx.compose.ui.tooling)

    // Steam
    implementation(libs.javasteam)
    implementation(libs.javasteam.depotdownloader)
    implementation(libs.protobuf.java)
    implementation(libs.spongycastle)
    implementation(libs.xz)

    // Networking
    implementation(libs.okhttp)
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.cio)
    implementation(libs.ktor.client.websockets)

    // DI
    implementation(libs.koin.android)
    implementation(libs.koin.androidx.compose)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // QR Code
    implementation(libs.zxing.core)

    // Image loading
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)

    // Widget
    implementation(libs.androidx.glance.appwidget)
    implementation(libs.androidx.glance.material3)
    implementation(libs.androidx.work.runtime)

    // Shizuku
    implementation(libs.shizuku.api)
    implementation(libs.shizuku.provider)

    // Testing
    testImplementation(libs.junit)
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    // M17: Compose UI testing invokes Espresso internally. Pre-3.7 Espresso uses
    // reflection on InputManager.getInstance(), absent on some Android versions/ROMs.
    // Keep this test-only; production/runtime and release signing are unchanged.
    androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

ktlint { android.set(true) }
