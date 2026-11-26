import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: settingsDialog
    modal: true
    focus: true
    anchors.centerIn: parent
    width: 460
    height: 410
    padding: 24

    background: Rectangle {
        color: "#0A1424"
        radius: 14
        border.color: "#1E3A5F"
        border.width: 1
    }

    property string selectedLang: primeBridge.languageMode
    property string selectedProfile: primeBridge.memoryProfile
    property bool clapChecked: primeBridge.doubleClapEnabled

    onOpened: {
        selectedLang = primeBridge.languageMode
        selectedProfile = primeBridge.memoryProfile
        clapChecked = primeBridge.doubleClapEnabled
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

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

        // Activation Option: Double-Clap
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "Double-Clap Activation (Config)"
                    color: "#DCEBFF"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }
                Text {
                    text: "Audio hardware is inactive in Phase 03. Wake-word is deferred."
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
                            font.pixelSize: 12
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        // Hardware Memory Profile (M1 8GB)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: "M1 8GB Memory Profile (For Future Local AI)"
                color: "#DCEBFF"
                font.pixelSize: 13
                font.weight: Font.Medium
            }
            RowLayout {
                spacing: 8
                Repeater {
                    model: [
                        { label: "Eco (1.5B)", value: "eco" },
                        { label: "Balanced (3B-4B)", value: "balanced" },
                        { label: "Heavy (7B Warn)", value: "heavy" }
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
                            font.pixelSize: 12
                            leftPadding: 8
                            rightPadding: 8
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: "Privacy: Microphone, Camera & Screen Recording permissions are NOT requested in Phase 03."
            color: "#57B894"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Button {
                text: "Save Local Config"
                onClicked: {
                    primeBridge.savePreferences(
                        settingsDialog.selectedLang,
                        settingsDialog.selectedProfile,
                        settingsDialog.clapChecked
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
