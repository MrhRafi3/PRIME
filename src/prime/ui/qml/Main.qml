import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: mainWindow
    width: 1180
    height: 780
    minimumWidth: 980
    minimumHeight: 680
    visible: true
    title: "PRIME — Personal Local Assistant"
    color: "#050A12"

    SettingsDialog {
        id: settingsDialog
    }

    Shortcut {
        sequence: primeBridge.pttShortcut
        onActivated: primeBridge.togglePushToTalk()
    }

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
                                if (primeBridge.assistantState === "transcribing") return "#38BDF8"
                                if (primeBridge.assistantState === "thinking") return "#F59E0B"
                                if (primeBridge.assistantState === "speaking") return "#F43F5E"
                                if (primeBridge.assistantState === "error") return "#EF4444"
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

                // Mic monitoring badge (visible when recording or double-clap active)
                Rectangle {
                    visible: primeBridge.isRecording || primeBridge.doubleClapMonitoring
                    radius: 6
                    color: "#221018"
                    border.color: "#F43F5E"
                    border.width: 1
                    implicitWidth: micLiveText.implicitWidth + 18
                    implicitHeight: 28

                    Text {
                        id: micLiveText
                        anchors.centerIn: parent
                        text: primeBridge.isRecording
                              ? ("MIC LIVE • " + primeBridge.recordingDurationText)
                              : "MIC MONITORING: DOUBLE-CLAP"
                        color: "#FDA4AF"
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.1
                    }
                }

                Item { Layout.fillWidth: true }

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

            // -------- LEFT COLUMN --------
            ColumnLayout {
                Layout.fillWidth: false
                Layout.preferredWidth: 420
                Layout.minimumWidth: 380
                Layout.maximumWidth: 440
                Layout.fillHeight: true
                spacing: 12

                // 2. CENTRAL HUD PANEL
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 240
                    color: "#CC091220"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        JarvisHud {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            stateName: primeBridge.assistantState
                            aiConnected: primeBridge.aiBackendConnected
                            micLevel: primeBridge.micLevel
                        }

                        // Runtime status + Model Load/Unload bar
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 62
                            radius: 8
                            color: "#0E1B2F"
                            border.color: primeBridge.runtimeStateText === "Error" ? "#7F1D1D" : "#1B3354"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: primeBridge.aiBackendConnected
                                              ? ("AI: " + primeBridge.runtimeStateText.toUpperCase())
                                              : ("AI ENGINE: " + primeBridge.runtimeStateText.toUpperCase())
                                        color: {
                                            if (primeBridge.runtimeStateText === "Error") return "#F87171"
                                            if (primeBridge.aiBackendConnected) return "#34D399"
                                            if (primeBridge.isModelAvailable) return "#38BDF8"
                                            return "#F59E0B"
                                        }
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.0
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: primeBridge.tokensPerSecText + " • " + primeBridge.lastTokenCount + " tok"
                                        color: "#8FA9C9"
                                        font.pixelSize: 10
                                        font.family: "Menlo"
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: "Model: " + primeBridge.activeModelName
                                        color: "#CBE4FF"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Button {
                                        Layout.preferredHeight: 24
                                        text: primeBridge.aiBackendConnected ? "Unload" : "Load Model"
                                        enabled: primeBridge.aiBackendConnected || primeBridge.isModelAvailable
                                        onClicked: {
                                            if (primeBridge.aiBackendConnected) {
                                                primeBridge.unloadModel()
                                            } else {
                                                primeBridge.loadModel()
                                            }
                                        }
                                        background: Rectangle {
                                            color: parent.enabled
                                                   ? (parent.hovered ? "#153254" : "#102540")
                                                   : "#0A1424"
                                            radius: 5
                                            border.color: parent.enabled ? "#2B568A" : "#162A44"
                                            border.width: 1
                                        }
                                        contentItem: Text {
                                            text: parent.text
                                            color: parent.enabled ? "#E2F1FF" : "#4E6888"
                                            font.pixelSize: 10
                                            font.weight: Font.Medium
                                            leftPadding: 8
                                            rightPadding: 8
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // 4. ACTIVATION & VOICE CONTROLS
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 210
                    color: "#CC0B1526"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "VOICE & ACTIVATION"
                                color: "#7E9CBE"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.8
                                Layout.fillWidth: true
                            }
                            Text {
                                text: "Mic: " + primeBridge.micPermissionText
                                color: primeBridge.micPermissionText === "Granted" ? "#34D399" : "#F59E0B"
                                font.pixelSize: 10
                            }
                        }

                        // Hold-to-talk + Cancel + Stop TTS
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Button {
                                id: pttButton
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                text: primeBridge.isRecording
                                      ? ("Release to Transcribe (" + primeBridge.recordingDurationText + ")")
                                      : (primeBridge.isTranscribing ? "Transcribing..." : "Hold to Talk (" + primeBridge.pttShortcut + ")")
                                enabled: !primeBridge.isTranscribing
                                onPressed: primeBridge.startPushToTalk()
                                onReleased: primeBridge.releasePushToTalk()
                                background: Rectangle {
                                    color: primeBridge.isRecording
                                           ? "#0E4866"
                                           : (pttButton.hovered ? "#132742" : "#0E1C30")
                                    radius: 8
                                    border.color: primeBridge.isRecording ? "#22D3EE" : "#22436B"
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: pttButton.text
                                    color: primeBridge.isRecording ? "#E2F8FF" : "#CBE4FF"
                                    font.pixelSize: 11
                                    font.weight: Font.Medium
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Button {
                                visible: primeBridge.isRecording || primeBridge.isTranscribing
                                Layout.preferredHeight: 38
                                Layout.preferredWidth: 74
                                text: "Cancel"
                                onClicked: primeBridge.cancelVoiceInput()
                                background: Rectangle {
                                    color: "#7F1D1D"
                                    radius: 8
                                    border.color: "#F87171"
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: "#FFFFFF"
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Button {
                                visible: primeBridge.isSpeaking
                                Layout.preferredHeight: 38
                                Layout.preferredWidth: 84
                                text: "Stop Voice"
                                onClicked: primeBridge.stopSpeaking()
                                background: Rectangle {
                                    color: "#881337"
                                    radius: 8
                                    border.color: "#FB7185"
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: "#FFFFFF"
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }

                        // Live Audio Level Bar
                        Rectangle {
                            Layout.fillWidth: true
                            height: 5
                            radius: 2.5
                            color: "#122238"
                            Rectangle {
                                width: parent.width * Math.min(1.0, primeBridge.micLevel)
                                height: parent.height
                                radius: 2.5
                                color: "#22D3EE"
                            }
                        }

                        // STT + Double-Clap Status & Controls
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text {
                                text: "STT: " + primeBridge.sttModelSlug
                                color: "#8FA9C9"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Button {
                                Layout.preferredHeight: 22
                                text: primeBridge.sttLoaded ? "Unload STT" : "Load STT"
                                enabled: primeBridge.sttLoaded || primeBridge.sttModelAvailable
                                onClicked: primeBridge.sttLoaded ? primeBridge.unloadSttModel() : primeBridge.loadSttModel()
                                background: Rectangle {
                                    color: parent.enabled ? "#102540" : "#0A1424"
                                    radius: 4
                                    border.color: parent.enabled ? "#2B568A" : "#162A44"
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: parent.enabled ? "#CBE4FF" : "#4E6888"
                                    font.pixelSize: 10
                                    leftPadding: 6
                                    rightPadding: 6
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text {
                                text: "Double-Clap: " + primeBridge.doubleClapStatusText
                                color: primeBridge.doubleClapMonitoring ? "#FDA4AF" : (primeBridge.doubleClapEnabled ? "#A7C5E8" : "#64748B")
                                font.pixelSize: 10
                                Layout.fillWidth: true
                            }
                            Button {
                                Layout.preferredHeight: 22
                                text: primeBridge.doubleClapMonitoring ? "Stop Monitor" : "Monitor"
                                enabled: primeBridge.doubleClapEnabled || primeBridge.doubleClapMonitoring
                                onClicked: primeBridge.toggleDoubleClapMonitoring()
                                background: Rectangle {
                                    color: primeBridge.doubleClapMonitoring ? "#7F1D1D" : (parent.enabled ? "#102540" : "#0A1424")
                                    radius: 4
                                    border.color: primeBridge.doubleClapMonitoring ? "#F87171" : (parent.enabled ? "#2B568A" : "#162A44")
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: parent.enabled ? "#E2F1FF" : "#4E6888"
                                    font.pixelSize: 10
                                    leftPadding: 6
                                    rightPadding: 6
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }

                // 5. SYSTEM INFORMATION
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 138
                    color: "#CC0B1526"
                    radius: 14
                    border.color: "#162B47"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

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
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "CPU Load"; color: "#8FA9C9"; font.pixelSize: 11; Layout.fillWidth: true }
                                Text { text: primeBridge.cpuText; color: "#E2F1FF"; font.pixelSize: 11; font.family: "Menlo" }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 4; radius: 2; color: "#122238"
                                Rectangle { width: parent.width * primeBridge.cpuRatio; height: parent.height; radius: 2; color: "#38BDF8" }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Unified Memory"; color: "#8FA9C9"; font.pixelSize: 11; Layout.fillWidth: true }
                                Text { text: primeBridge.memoryText; color: "#E2F1FF"; font.pixelSize: 11; font.family: "Menlo" }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 4; radius: 2; color: "#122238"
                                Rectangle {
                                    width: parent.width * primeBridge.memoryRatio
                                    height: parent.height
                                    radius: 2
                                    color: primeBridge.memoryRatio > 0.85 ? "#F59E0B" : "#22D3EE"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Power / Battery"; color: "#8FA9C9"; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: primeBridge.batteryText; color: "#E2F1FF"; font.pixelSize: 11; font.family: "Menlo" }
                        }
                    }
                }
            }

            // -------- RIGHT COLUMN: CONVERSATION PANEL --------
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
                            text: "CONVERSATION & VOICE LOG"
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
                            text: primeBridge.isModelAvailable
                                  ? ("Local model '" + primeBridge.activeModelName + "' is installed. Click 'Load Model' to enable offline MLX inference.")
                                  : "No local MLX model is installed yet. Submitted messages are saved locally in SQLite without fabricating AI replies."
                            color: "#FCD34D"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }
                    }

                    // Transcription preview bar
                    Rectangle {
                        Layout.fillWidth: true
                        visible: primeBridge.transcriptionPreview.length > 0
                        implicitHeight: previewText.implicitHeight + 14
                        color: "#0C2136"
                        radius: 8
                        border.color: "#1D4D75"
                        border.width: 1

                        Text {
                            id: previewText
                            anchors.fill: parent
                            anchors.margins: 7
                            text: "VOICE PREVIEW: " + primeBridge.transcriptionPreview
                            color: "#7DD3FC"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }

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
                                text: "Type a message in Bangla or English below, or hold Push-to-Talk to speak offline via Whisper & AVSpeech."
                                color: "#607D9F"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

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
                            text: primeBridge.isGenerating ? "Stop" : "Send"
                            enabled: primeBridge.isGenerating || promptInput.text.trim().length > 0
                            onClicked: {
                                if (primeBridge.isGenerating) {
                                    primeBridge.cancelGeneration()
                                } else {
                                    primeBridge.sendMessage(promptInput.text)
                                    promptInput.text = ""
                                }
                            }
                            background: Rectangle {
                                color: primeBridge.isGenerating
                                       ? "#991B1B"
                                       : (sendBtn.enabled
                                          ? (sendBtn.hovered ? "#0284C7" : "#0369A1")
                                          : "#0E1A2B")
                                radius: 9
                                border.color: primeBridge.isGenerating
                                              ? "#F87171"
                                              : (sendBtn.enabled ? "#38BDF8" : "#182D49")
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
