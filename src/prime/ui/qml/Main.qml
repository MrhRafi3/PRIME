import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: mainWindow
    width: 1160
    height: 760
    minimumWidth: 960
    minimumHeight: 640
    visible: true
    title: "PRIME — Personal Local Assistant"
    color: "#050A12"

    SettingsDialog {
        id: settingsDialog
    }

    // Subtle deep navy radial atmosphere
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#070F1C" }
            GradientStop { position: 0.6; color: "#050A12" }
            GradientStop { position: 1.0; color: "#03070E" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        // ==================== 1. HEADER ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#CC0B1526"
            radius: 12
            border.color: "#172D4A"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 14

                // Minimal PRIME mark + title
                RowLayout {
                    spacing: 10
                    Rectangle {
                        width: 28
                        height: 28
                        radius: 14
                        color: "transparent"
                        border.color: "#38BDF8"
                        border.width: 2
                        Rectangle {
                            anchors.centerIn: parent
                            width: 10
                            height: 10
                            radius: 5
                            color: "#38BDF8"
                        }
                    }
                    ColumnLayout {
                        spacing: 0
                        Text {
                            text: primeBridge.appName
                            color: "#E2F1FF"
                            font.pixelSize: 17
                            font.weight: Font.Bold
                            font.letterSpacing: 3.5
                        }
                        Text {
                            text: "LOCAL HUD INTERFACE"
                            color: "#607D9F"
                            font.pixelSize: 10
                            font.letterSpacing: 1.8
                        }
                    }
                }

                // State badge
                Rectangle {
                    radius: 6
                    color: "#0F2238"
                    border.color: primeBridge.assistantState === "listening" ? "#22D3EE" : "#1E3A5F"
                    border.width: 1
                    implicitWidth: statusPillRow.implicitWidth + 20
                    implicitHeight: 28

                    RowLayout {
                        id: statusPillRow
                        anchors.centerIn: parent
                        spacing: 7
                        Rectangle {
                            width: 7
                            height: 7
                            radius: 3.5
                            color: {
                                if (primeBridge.assistantState === "listening") return "#22D3EE"
                                if (primeBridge.assistantState === "thinking") return "#F59E0B"
                                if (primeBridge.assistantState === "speaking") return "#F43F5E"
                                return "#38BDF8"
                            }
                        }
                        Text {
                            text: "STATUS: " + primeBridge.assistantStateLabel
                            color: "#CBE4FF"
                            font.pixelSize: 11
                            font.weight: Font.Medium
                            font.letterSpacing: 1.2
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Clock
                ColumnLayout {
                    spacing: 0
                    Layout.alignment: Qt.AlignVCenter
                    Text {
                        text: primeBridge.currentTimeText
                        color: "#E2F1FF"
                        font.pixelSize: 15
                        font.family: "Menlo"
                        horizontalAlignment: Text.AlignRight
                        Layout.alignment: Qt.AlignRight
                    }
                    Text {
                        text: primeBridge.currentDateText
                        color: "#6A87A9"
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignRight
                        Layout.alignment: Qt.AlignRight
                    }
                }

                // Settings trigger
                Button {
                    text: "Settings"
                    onClicked: settingsDialog.open()
                    background: Rectangle {
                        color: parent.hovered ? "#152842" : "#0F1D32"
                        radius: 8
                        border.color: "#22436B"
                        border.width: 1
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#CBE4FF"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                        leftPadding: 12
                        rightPadding: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // ==================== MAIN WORKSPACE ====================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            // -------- LEFT COLUMN: CENTRAL HUD + ACTIVATION + SYSTEM METRICS --------
            ColumnLayout {
                Layout.fillWidth: false
                Layout.preferredWidth: 410
                Layout.minimumWidth: 370
                Layout.maximumWidth: 430
                Layout.fillHeight: true
                spacing: 14

                // 2. CENTRAL HUD PANEL
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 280
                    color: "#CC091220"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        JarvisHud {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            stateName: primeBridge.assistantState
                            aiConnected: primeBridge.aiBackendConnected
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            radius: 8
                            color: "#0E1B2F"
                            border.color: "#1B3354"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: primeBridge.aiBackendConnected
                                      ? "LOCAL AI ENGINE: CONNECTED"
                                      : "AI ENGINE: NOT CONNECTED (PHASE 03)"
                                color: primeBridge.aiBackendConnected ? "#34D399" : "#F59E0B"
                                font.pixelSize: 11
                                font.weight: Font.Medium
                                font.letterSpacing: 1.1
                            }
                        }
                    }
                }

                // 4. ACTIVATION CONTROLS
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 150
                    color: "#CC0B1526"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        Text {
                            text: "ACTIVATION CONTROLS"
                            color: "#7E9CBE"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.8
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Button {
                                id: pttButton
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                text: primeBridge.pushToTalkPressed
                                      ? "Push-to-Talk: ACTIVE (Release/Click)"
                                      : "Push-to-Talk (UI State)"
                                onClicked: primeBridge.togglePushToTalk()
                                background: Rectangle {
                                    color: primeBridge.pushToTalkPressed
                                           ? "#0E4866"
                                           : (pttButton.hovered ? "#132742" : "#0E1C30")
                                    radius: 8
                                    border.color: primeBridge.pushToTalkPressed ? "#22D3EE" : "#22436B"
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: pttButton.text
                                    color: primeBridge.pushToTalkPressed ? "#E2F8FF" : "#CBE4FF"
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Push-to-Talk:"
                                    color: "#7E9CBE"
                                    font.pixelSize: 11
                                }
                                Text {
                                    text: primeBridge.pushToTalkStatusText
                                    color: "#A7C5E8"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Double-Clap:"
                                    color: "#7E9CBE"
                                    font.pixelSize: 11
                                }
                                Text {
                                    text: primeBridge.doubleClapStatusText
                                    color: primeBridge.doubleClapEnabled ? "#A7C5E8" : "#64748B"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }
                    }
                }

                // 5. SYSTEM INFORMATION
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 150
                    color: "#CC0B1526"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "SYSTEM TELEMETRY (LOCAL)"
                                color: "#7E9CBE"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.8
                                Layout.fillWidth: true
                            }
                            Text {
                                text: primeBridge.memoryProfile.toUpperCase() + " • " + primeBridge.languageMode
                                color: "#38BDF8"
                                font.pixelSize: 10
                                font.letterSpacing: 1.0
                            }
                        }

                        // CPU row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "CPU Load"; color: "#8FA9C9"; font.pixelSize: 12; Layout.fillWidth: true }
                                Text { text: primeBridge.cpuText; color: "#E2F1FF"; font.pixelSize: 12; font.family: "Menlo" }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2.5; color: "#122238"
                                Rectangle {
                                    width: parent.width * primeBridge.cpuRatio
                                    height: parent.height
                                    radius: 2.5
                                    color: "#38BDF8"
                                }
                            }
                        }

                        // Memory row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Unified Memory"; color: "#8FA9C9"; font.pixelSize: 12; Layout.fillWidth: true }
                                Text { text: primeBridge.memoryText; color: "#E2F1FF"; font.pixelSize: 12; font.family: "Menlo" }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2.5; color: "#122238"
                                Rectangle {
                                    width: parent.width * primeBridge.memoryRatio
                                    height: parent.height
                                    radius: 2.5
                                    color: primeBridge.memoryRatio > 0.85 ? "#F59E0B" : "#22D3EE"
                                }
                            }
                        }

                        // Battery row
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Power / Battery"; color: "#8FA9C9"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: primeBridge.batteryText; color: "#E2F1FF"; font.pixelSize: 12; font.family: "Menlo" }
                        }
                    }
                }
            }

            // -------- RIGHT COLUMN: 3. CONVERSATION PANEL --------
            Rectangle {
                Layout.fillWidth: true
                Layout.minimumWidth: 440
                Layout.fillHeight: true
                color: "#CC091220"
                radius: 14
                border.color: "#162B47"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "CONVERSATION & COMMAND LOG"
                            color: "#7E9CBE"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.8
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "Clear View"
                            visible: messageList.count > 0
                            onClicked: primeBridge.clearConversationView()
                            background: Rectangle {
                                color: parent.hovered ? "#152842" : "#0F1D32"
                                radius: 6
                                border.color: "#22436B"
                                border.width: 1
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#8FA9C9"
                                font.pixelSize: 11
                                leftPadding: 10
                                rightPadding: 10
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }

                    // Explicit offline/unavailable banner when AI engine is not connected
                    Rectangle {
                        Layout.fillWidth: true
                        visible: !primeBridge.aiBackendConnected
                        implicitHeight: offlineNoticeText.implicitHeight + 18
                        color: "#1C1A10"
                        radius: 8
                        border.color: "#785315"
                        border.width: 1

                        Text {
                            id: offlineNoticeText
                            anchors.fill: parent
                            anchors.margins: 9
                            text: "Local AI inference engine is not connected in Phase 03. Submitted messages are recorded locally in SQLite without generating fabricated replies."
                            color: "#FCD34D"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }
                    }

                    // Conversation history list
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ListView {
                            id: messageList
                            anchors.fill: parent
                            spacing: 10
                            clip: true
                            model: primeBridge.messagesModel

                            onCountChanged: {
                                if (count > 0) positionViewAtEnd()
                            }

                            delegate: Rectangle {
                                required property string msgRole
                                required property string msgText
                                required property string msgTime
                                required property string msgKind

                                width: messageList.width
                                implicitHeight: msgCol.implicitHeight + 20
                                radius: 10
                                color: msgKind === "notice" ? "#151821" : "#0F1E34"
                                border.color: msgKind === "notice" ? "#6B4E1B" : "#1E3A5F"
                                border.width: 1

                                ColumnLayout {
                                    id: msgCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: msgRole.toUpperCase()
                                            color: msgKind === "notice" ? "#FBBF24" : "#38BDF8"
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            font.letterSpacing: 1.3
                                            Layout.fillWidth: true
                                        }
                                        Text {
                                            text: msgTime
                                            color: "#607D9F"
                                            font.pixelSize: 10
                                            font.family: "Menlo"
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: msgText
                                        color: "#E2F1FF"
                                        font.pixelSize: 13
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }

                        // Empty state when no messages submitted yet
                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            visible: messageList.count === 0
                            width: Math.min(parent.width - 40, 380)

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "PRIME DESKTOP READY"
                                color: "#9EC2E6"
                                font.pixelSize: 14
                                font.weight: Font.Medium
                                font.letterSpacing: 2.0
                            }
                            Text {
                                width: parent.width
                                text: "Type a message in Bangla or English below to test local session logging, or use the Push-to-Talk control to inspect UI state transitions."
                                color: "#607D9F"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    // Text Input + Send Button
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            id: promptInput
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            placeholderText: "Enter command or message (Bangla / English)..."
                            placeholderTextColor: "#536E8F"
                            color: "#E2F1FF"
                            font.pixelSize: 13
                            leftPadding: 14
                            rightPadding: 14

                            background: Rectangle {
                                color: "#0B1626"
                                radius: 9
                                border.color: promptInput.activeFocus ? "#38BDF8" : "#1B3354"
                                border.width: 1
                            }

                            onAccepted: {
                                if (text.trim().length > 0) {
                                    primeBridge.sendMessage(text)
                                    text = ""
                                }
                            }
                        }

                        Button {
                            id: sendBtn
                            Layout.preferredHeight: 42
                            Layout.preferredWidth: 96
                            text: "Send"
                            enabled: promptInput.text.trim().length > 0
                            onClicked: {
                                primeBridge.sendMessage(promptInput.text)
                                promptInput.text = ""
                            }
                            background: Rectangle {
                                color: sendBtn.enabled
                                       ? (sendBtn.hovered ? "#0284C7" : "#0369A1")
                                       : "#0E1A2B"
                                radius: 9
                                border.color: sendBtn.enabled ? "#38BDF8" : "#182D49"
                                border.width: 1
                            }
                            contentItem: Text {
                                text: sendBtn.text
                                color: sendBtn.enabled ? "#FFFFFF" : "#4E6888"
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }
        }

        // ==================== 6. STATUS / FOOTER ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: "#CC08101C"
            radius: 10
            border.color: "#13263E"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 16

                RowLayout {
                    spacing: 6
                    Rectangle { width: 7; height: 7; radius: 3.5; color: "#34D399" }
                    Text {
                        text: primeBridge.localPrivacyText
                        color: "#76D7AE"
                        font.pixelSize: 11
                        font.weight: Font.Medium
                        font.letterSpacing: 1.0
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: primeBridge.backendStatusText
                    color: "#7E9CBE"
                    font.pixelSize: 11
                }

                Text {
                    text: "•"
                    color: "#334E70"
                    font.pixelSize: 11
                }

                Text {
                    text: primeBridge.versionText + " (" + primeBridge.bundleId + ")"
                    color: "#607D9F"
                    font.pixelSize: 11
                    font.family: "Menlo"
                }
            }
        }
    }
}
