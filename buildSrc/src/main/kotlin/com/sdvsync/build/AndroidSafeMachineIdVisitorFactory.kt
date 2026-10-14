package com.sdvsync.build

import com.android.build.api.instrumentation.AsmClassVisitorFactory
import com.android.build.api.instrumentation.ClassContext
import com.android.build.api.instrumentation.ClassData
import com.android.build.api.instrumentation.InstrumentationParameters
import org.objectweb.asm.ClassVisitor
import org.objectweb.asm.MethodVisitor
import org.objectweb.asm.Opcodes

/** Rewrites JavaSteam 1.8.0 HardwareUtils.getMachineID(): byte[]. */
abstract class AndroidSafeMachineIdVisitorFactory : AsmClassVisitorFactory<InstrumentationParameters.None> {
    override fun isInstrumentable(classData: ClassData): Boolean =
        classData.className == "in.dragonbra.javasteam.util.HardwareUtils"

    override fun createClassVisitor(classContext: ClassContext, nextClassVisitor: ClassVisitor): ClassVisitor =
        object : ClassVisitor(Opcodes.ASM9, nextClassVisitor) {
            private var didRewrite = false
            override fun visitMethod(
                access: Int, name: String, descriptor: String, signature: String?, exceptions: Array<out String>?
            ): MethodVisitor? {
                if (name == "getMachineID" && descriptor == "()[B") {
                    didRewrite = true
                    val mv = super.visitMethod(access, name, descriptor, signature, exceptions)
                    mv.visitCode()
                    mv.visitMethodInsn(
                        Opcodes.INVOKESTATIC,
                        "com/sdvsync/steam/AndroidSteamMachineId",
                        "getMachineId",
                        "()[B",
                        false
                    )
                    mv.visitInsn(Opcodes.ARETURN)
                    mv.visitMaxs(1, 1)
                    mv.visitEnd()
                    // Drop original method body, including Linux hardware execution path.
                    return null
                }
                return super.visitMethod(access, name, descriptor, signature, exceptions)
            }
            override fun visitEnd() {
                check(didRewrite) { "JavaSteam HardwareUtils API changed; refusing unsafe build" }
                super.visitEnd()
            }
        }
}
