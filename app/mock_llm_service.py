"""Rule-based mock LLM service.

Structured behind the LLMService protocol so a real Claude-backed
implementation (e.g. ClaudeLLMService) can be swapped in later without
touching the API layer.
"""

from __future__ import annotations

from typing import Protocol

from app.schemas import AnalyzeErrorResponse, CodePatch, ErrorContext, Fix


class LLMService(Protocol):
    """Contract any error-analysis backend (mock or real) must satisfy."""

    def analyze(self, error_text: str, context: ErrorContext | None) -> AnalyzeErrorResponse:
        ...


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


class MockLLMService:
    """Keyword/rule-based stand-in for a real LLM call."""

    GRADLE_KEYWORDS = ["could not resolve", "execution failed for task", "version conflict"]
    COMPOSE_KEYWORDS = ["compose", "preview", "@preview", "could not find method"]
    ADB_KEYWORDS = ["device", "adb", "offline", "installation failed"]

    def analyze(self, error_text: str, context: ErrorContext | None) -> AnalyzeErrorResponse:
        if _contains_any(error_text, self.GRADLE_KEYWORDS):
            return self._gradle_sync_failed(context)
        if _contains_any(error_text, self.COMPOSE_KEYWORDS):
            return self._compose_preview_not_rendering(context)
        if _contains_any(error_text, self.ADB_KEYWORDS):
            return self._adb_device_not_found(context)
        return self._generic_fallback(error_text)

    def _gradle_sync_failed(self, context: ErrorContext | None) -> AnalyzeErrorResponse:
        agp = (context.agp_version if context else None) or "8.x"
        gradle = (context.gradle_version if context else None) or "8.x"
        return AnalyzeErrorResponse(
            error_type="Gradle sync failed",
            explanation=(
                "Gradle could not resolve one or more dependencies or a task failed during "
                "sync. This is usually caused by a version mismatch between AGP, Gradle, and "
                "Kotlin, a stale dependency cache, or a missing/unreachable repository."
            ),
            fixes=[
                Fix(
                    title="Align AGP, Gradle, and Kotlin versions",
                    steps=[
                        f"Confirm your AGP version ({agp}) is compatible with Gradle ({gradle}).",
                        "Open the AGP/Gradle compatibility table in the Android docs and match versions.",
                        "Update gradle/wrapper/gradle-wrapper.properties and the AGP version in build.gradle.kts.",
                        "Re-sync the project.",
                    ],
                    code_patches=[
                        CodePatch(
                            file="build.gradle.kts (project)",
                            code=(
                                "plugins {\n"
                                "    id(\"com.android.application\") version \"8.5.2\" apply false\n"
                                "    id(\"org.jetbrains.kotlin.android\") version \"1.9.24\" apply false\n"
                                "}"
                            ),
                        ),
                        CodePatch(
                            file="gradle/wrapper/gradle-wrapper.properties",
                            code="distributionUrl=https\\://services.gradle.org/distributions/gradle-8.7-bin.zip",
                        ),
                    ],
                    commands=["./gradlew --version", "./gradlew clean"],
                ),
                Fix(
                    title="Clear caches and retry with a clean dependency resolution",
                    steps=[
                        "Stop any running Gradle daemons.",
                        "Delete the local Gradle and build caches.",
                        "Re-run sync with --refresh-dependencies to force re-resolution.",
                    ],
                    code_patches=[],
                    commands=[
                        "./gradlew --stop",
                        "rm -rf ~/.gradle/caches/",
                        "./gradlew build --refresh-dependencies",
                    ],
                ),
            ],
        )

    def _compose_preview_not_rendering(self, context: ErrorContext | None) -> AnalyzeErrorResponse:
        compose = (context.compose_version if context else None) or "2024.x BOM"
        return AnalyzeErrorResponse(
            error_type="Compose preview not rendering",
            explanation=(
                "The @Preview composable failed to render in the IDE. This is typically caused "
                "by a mismatch between the Compose compiler and Kotlin versions, a missing "
                "Compose BOM entry, or an unresolved method used inside the preview function."
            ),
            fixes=[
                Fix(
                    title="Match Compose compiler version to your Kotlin version",
                    steps=[
                        f"Check that your Compose BOM/compiler ({compose}) supports your Kotlin version.",
                        "Update the composeOptions block in your module's build.gradle.kts.",
                        "Invalidate caches and restart Android Studio.",
                    ],
                    code_patches=[
                        CodePatch(
                            file="app/build.gradle.kts",
                            code=(
                                "composeOptions {\n"
                                "    kotlinCompilerExtensionVersion = \"1.5.14\"\n"
                                "}"
                            ),
                        )
                    ],
                    commands=[],
                ),
                Fix(
                    title="Isolate the preview from runtime dependencies",
                    steps=[
                        "Ensure the @Preview function does not call methods requiring a real Activity/Context.",
                        "Wrap data with hardcoded sample values instead of ViewModel state for the preview.",
                        "Rebuild the preview surface (Build > Rebuild Project).",
                    ],
                    code_patches=[
                        CodePatch(
                            file="ExampleScreen.kt",
                            code=(
                                "@Preview(showBackground = true)\n"
                                "@Composable\n"
                                "fun ExampleScreenPreview() {\n"
                                "    ExampleScreen(state = ExampleState.sample())\n"
                                "}"
                            ),
                        )
                    ],
                    commands=[],
                ),
            ],
        )

    def _adb_device_not_found(self, context: ErrorContext | None) -> AnalyzeErrorResponse:
        return AnalyzeErrorResponse(
            error_type="ADB device not found / installation failed",
            explanation=(
                "ADB cannot see a connected device or emulator, or the app failed to install. "
                "This usually means the ADB server is stuck, USB debugging isn't authorized, or "
                "the device shows as 'offline'."
            ),
            fixes=[
                Fix(
                    title="Restart the ADB server and reconnect",
                    steps=[
                        "Kill and restart the ADB server.",
                        "Unplug and replug the device (or cold-boot the emulator).",
                        "Re-authorize USB debugging on the device if prompted.",
                        "Confirm the device now shows as 'device' (not 'offline') in adb devices.",
                    ],
                    code_patches=[],
                    commands=["adb kill-server", "adb start-server", "adb devices"],
                ),
                Fix(
                    title="Reinstall the app cleanly",
                    steps=[
                        "Uninstall the existing debug build from the device.",
                        "Rebuild and reinstall the APK.",
                    ],
                    code_patches=[],
                    commands=[
                        "adb uninstall com.androidaid.app",
                        "./gradlew installDebug",
                    ],
                ),
            ],
        )

    def _generic_fallback(self, error_text: str) -> AnalyzeErrorResponse:
        snippet = error_text.strip().splitlines()[0][:160]
        return AnalyzeErrorResponse(
            error_type="Unrecognized error",
            explanation=(
                f"This error wasn't matched to a known category based on: \"{snippet}\". "
                "Below are general steps that resolve most Android Studio build/runtime issues."
            ),
            fixes=[
                Fix(
                    title="General troubleshooting pass",
                    steps=[
                        "Read the full stack trace top to bottom for the first 'Caused by:' line.",
                        "Search the exact exception class/message in the error.",
                        "Invalidate caches and restart Android Studio.",
                        "Try a clean rebuild.",
                    ],
                    code_patches=[],
                    commands=["./gradlew clean build"],
                ),
                Fix(
                    title="Isolate the change that introduced the error",
                    steps=[
                        "Check recent git changes (dependency bumps, new plugins, manifest edits).",
                        "Temporarily revert the most recent change and re-sync to confirm it's the cause.",
                    ],
                    code_patches=[],
                    commands=["git diff HEAD~1"],
                ),
            ],
        )
