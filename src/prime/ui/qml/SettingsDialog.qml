import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: settingsDialog
    modal: true
    focus: true
    anchors.centerIn: parent
    width: 500
    height: 610
    padding: 22

    background: Rectangle {
        color: "#0A1424"
        radius: 14
        border.color: "#1E3A5F"
        border.width: 1
    }

    property string selectedLang: primeBridge.languageMode
    property string selectedProfile: primeBridge.memoryProfile
    property bool clapChecked: primeBridge.doubleClapEnabled
    property string selectedModel: primeBridge.selectedModelSlug
    property string selectedStt: primeBridge.sttModelSlug
    property bool ttsChecked: primeBridge.ttsEnabled
    property string selectedEnglishVoice: primeBridge.ttsEnglishVoice
    property real selectedTtsRate: primeBridge.ttsRate
    property real selectedTtsVolume: primeBridge.ttsVolume

    onOpened: {
        selectedLang = primeBridge.languageMode
        selectedProfile = primeBridge.memoryProfile
        clapChecked = primeBridge.doubleClapEnabled
        selectedModel = primeBridge.selectedModelSlug
        selectedStt = primeBridge.sttModelSlug
        ttsChecked = primeBridge.ttsEnabled
        selectedEnglishVoice = primeBridge.ttsEnglishVoice
        selectedTtsRate = primeBridge.ttsRate
        selectedTtsVolume = primeBridge.ttsVolume
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "PRIME SETTINGS"
                color: "#E2F1FF"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                font.letterSpacing: 2.5
                Layout.fillWidth: true
            }
            Button {
                text: "Close"
                onClicked: settingsDialog.close()
                background: Rectangle {
                    color: parent.hovered ? "#172A45" : "#0F1D32"
                    radius: 6
                    border.color: "#274B7A"
                    border.width: 1
                }
                contentItem: Text {
                    text: parent.text
                    color: "#94B8DB"
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#15263E" }

        // Double-Clap Opt-In
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "Double-Clap Activation (Opt-In)"
                    color: "#DCEBFF"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }
                Text {
                    text: "Disabled by default. Local RMS transient analysis only; zero audio saved."
                    color: "#6B86A8"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
            Switch {
                checked: settingsDialog.clapChecked
                onToggled: settingsDialog.clapChecked = checked
            }
        }

        // Language Priority
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: "Language Priority"
                color: "#DCEBFF"
                font.pixelSize: 13
                font.weight: Font.Medium
            }
            RowLayout {
                spacing: 8
                Repeater {
                    model: [
                        { label: "Bangla + English (bn-en)", value: "bn-en" },
                        { label: "English Only (en)", value: "en" }
                    ]
                    delegate: Button {
                        required property var modelData
                        text: modelData.label
                        onClicked: settingsDialog.selectedLang = modelData.value
                        background: Rectangle {
                            color: settingsDialog.selectedLang === modelData.value ? "#0E3352" : "#0E1A2B"
                            radius: 6
                            border.color: settingsDialog.selectedLang === modelData.value ? "#38BDF8" : "#1E3352"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.selectedLang === modelData.value ? "#E2F1FF" : "#8FA9C9"
                            font.pixelSize: 11
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        // Offline STT Model Selection
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: "Offline Whisper STT Model"
                color: "#DCEBFF"
                font.pixelSize: 13
                font.weight: Font.Medium
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: [
                        { label: "Small q5_1 (181 MB)", value: "whisper-small-q5_1" },
                        { label: "Large-v3-Turbo q5_0 (547 MB)", value: "whisper-large-v3-turbo-q5_0" }
                    ]
                    delegate: Button {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        onClicked: settingsDialog.selectedStt = modelData.value
                        background: Rectangle {
                            color: settingsDialog.selectedStt === modelData.value ? "#0E3352" : "#0E1A2B"
                            radius: 6
                            border.color: settingsDialog.selectedStt === modelData.value ? "#38BDF8" : "#1E3352"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.selectedStt === modelData.value ? "#E2F1FF" : "#8FA9C9"
                            font.pixelSize: 11
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        // Offline TTS Controls
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Offline Voice Output (AVSpeechSynthesizer)"
                    color: "#DCEBFF"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    Layout.fillWidth: true
                }
                Switch {
                    checked: settingsDialog.ttsChecked
                    onToggled: settingsDialog.ttsChecked = checked
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: "English Voice:"; color: "#8FA9C9"; font.pixelSize: 11 }
                Repeater {
                    model: ["Daniel", "Samantha", "Rishi"]
                    delegate: Button {
                        required property string modelData
                        text: modelData
                        onClicked: settingsDialog.selectedEnglishVoice = modelData
                        background: Rectangle {
                            color: settingsDialog.selectedEnglishVoice === modelData ? "#0E3352" : "#0E1A2B"
                            radius: 5
                            border.color: settingsDialog.selectedEnglishVoice === modelData ? "#38BDF8" : "#1E3352"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.selectedEnglishVoice === modelData ? "#E2F1FF" : "#8FA9C9"
                            font.pixelSize: 11
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
                Item { Layout.fillWidth: true }
                Text { text: "Bangla: Piya (Local)"; color: "#57B894"; font.pixelSize: 11 }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Text { text: "Rate " + settingsDialog.selectedTtsRate.toFixed(2); color: "#8FA9C9"; font.pixelSize: 11 }
                Slider {
                    from: 0.2
                    to: 0.85
                    value: settingsDialog.selectedTtsRate
                    onMoved: settingsDialog.selectedTtsRate = value
                    Layout.fillWidth: true
                }
                Text { text: "Vol " + Math.round(settingsDialog.selectedTtsVolume * 100) + "%"; color: "#8FA9C9"; font.pixelSize: 11 }
                Slider {
                    from: 0.0
                    to: 1.0
                    value: settingsDialog.selectedTtsVolume
                    onMoved: settingsDialog.selectedTtsVolume = value
                    Layout.fillWidth: true
                }
            }
        }

        // Local MLX LLM Selection
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: "Local MLX LLM & Memory Profile"
                color: "#DCEBFF"
                font.pixelSize: 13
                font.weight: Font.Medium
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: [
                        { label: "Qwen 2.5 1.5B (4-bit)", value: "qwen2.5-1.5b-4bit" },
                        { label: "Qwen 3 1.7B (4-bit)", value: "qwen3-1.7b-4bit" }
                    ]
                    delegate: Button {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        onClicked: settingsDialog.selectedModel = modelData.value
                        background: Rectangle {
                            color: settingsDialog.selectedModel === modelData.value ? "#0E3352" : "#0E1A2B"
                            radius: 6
                            border.color: settingsDialog.selectedModel === modelData.value ? "#38BDF8" : "#1E3352"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.selectedModel === modelData.value ? "#E2F1FF" : "#8FA9C9"
                            font.pixelSize: 11
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
            RowLayout {
                spacing: 8
                Repeater {
                    model: [
                        { label: "Eco (2200 MB)", value: "eco" },
                        { label: "Balanced (3200 MB)", value: "balanced" }
                    ]
                    delegate: Button {
                        required property var modelData
                        text: modelData.label
                        onClicked: settingsDialog.selectedProfile = modelData.value
                        background: Rectangle {
                            color: settingsDialog.selectedProfile === modelData.value ? "#0E3352" : "#0E1A2B"
                            radius: 6
                            border.color: settingsDialog.selectedProfile === modelData.value ? "#38BDF8" : "#1E3352"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.selectedProfile === modelData.value ? "#E2F1FF" : "#8FA9C9"
                            font.pixelSize: 11
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "100% local processing. No cloud STT/TTS."
                color: "#57B894"
                font.pixelSize: 11
                Layout.fillWidth: true
            }
            Button {
                text: "Save Local Config"
                onClicked: {
                    primeBridge.saveAllPreferences(
                        settingsDialog.selectedLang,
                        settingsDialog.selectedProfile,
                        settingsDialog.clapChecked,
                        settingsDialog.selectedModel,
                        settingsDialog.selectedStt,
                        settingsDialog.ttsChecked,
                        settingsDialog.selectedEnglishVoice,
                        settingsDialog.selectedTtsRate,
                        settingsDialog.selectedTtsVolume
                    )
                    settingsDialog.close()
                }
                background: Rectangle {
                    color: parent.hovered ? "#0284C7" : "#0369A1"
                    radius: 7
                }
                contentItem: Text {
                    text: parent.text
                    color: "#FFFFFF"
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    leftPadding: 14
                    rightPadding: 14
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
