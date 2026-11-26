import QtQuick

Item {
    id: hudRoot
    property string stateName: "idle"
    property bool aiConnected: false
    property real micLevel: 0.0

    readonly property color accentColor: {
        if (stateName === "listening") return "#22D3EE"
        if (stateName === "transcribing") return "#38BDF8"
        if (stateName === "thinking") return "#F59E0B"
        if (stateName === "speaking") return "#F43F5E"
        if (stateName === "error") return "#EF4444"
        return "#38BDF8"
    }
    readonly property color secondaryColor: stateName === "thinking" ? "#D97706" : "#1D4ED8"

    property real outerAngle: 0
    property real innerAngle: 0
    property real pulseScale: 1.0

    NumberAnimation on outerAngle {
        from: 0
        to: 360
        duration: hudRoot.stateName === "thinking" || hudRoot.stateName === "transcribing" ? 5500 : 18000
        loops: Animation.Infinite
        running: hudRoot.visible
    }

    NumberAnimation on innerAngle {
        from: 360
        to: 0
        duration: hudRoot.stateName === "listening" ? 6000 : 14000
        loops: Animation.Infinite
        running: hudRoot.visible
    }

    SequentialAnimation on pulseScale {
        loops: Animation.Infinite
        running: hudRoot.visible
        NumberAnimation {
            from: 0.96
            to: hudRoot.stateName === "listening" || hudRoot.stateName === "speaking" ? 1.06 : 1.02
            duration: hudRoot.stateName === "listening" || hudRoot.stateName === "speaking" ? 750 : 2200
            easing.type: Easing.InOutSine
        }
        NumberAnimation {
            from: hudRoot.stateName === "listening" || hudRoot.stateName === "speaking" ? 1.06 : 1.02
            to: 0.96
            duration: hudRoot.stateName === "listening" || hudRoot.stateName === "speaking" ? 750 : 2200
            easing.type: Easing.InOutSine
        }
    }

    onOuterAngleChanged: hudCanvas.requestPaint()
    onInnerAngleChanged: hudCanvas.requestPaint()
    onStateNameChanged: hudCanvas.requestPaint()
    onMicLevelChanged: hudCanvas.requestPaint()

    Canvas {
        id: hudCanvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d")
            var w = width
            var h = height
            var cx = w / 2
            var cy = h / 2
            var r = Math.min(w, h) * 0.45

            ctx.clearRect(0, 0, w, h)

            var grad = ctx.createRadialGradient(cx, cy, r * 0.05, cx, cy, r * 1.05)
            grad.addColorStop(0.0, Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.22))
            grad.addColorStop(0.55, Qt.rgba(hudRoot.secondaryColor.r, hudRoot.secondaryColor.g, hudRoot.secondaryColor.b, 0.08))
            grad.addColorStop(1.0, "transparent")
            ctx.fillStyle = grad
            ctx.beginPath()
            ctx.arc(cx, cy, r * 1.05, 0, Math.PI * 2)
            ctx.fill()

            ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.22)
            ctx.lineWidth = 1.2
            ctx.beginPath()
            ctx.arc(cx, cy, r * 0.96, 0, Math.PI * 2)
            ctx.stroke()

            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(hudRoot.outerAngle * Math.PI / 180)
            ctx.strokeStyle = hudRoot.accentColor
            ctx.lineWidth = 2.4
            for (var i = 0; i < 3; i++) {
                var a0 = i * (Math.PI * 2 / 3) + 0.18
                ctx.beginPath()
                ctx.arc(0, 0, r * 0.86, a0, a0 + 1.15)
                ctx.stroke()
            }
            ctx.restore()

            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(hudRoot.innerAngle * Math.PI / 180)
            ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.55)
            ctx.lineWidth = 1.6
            for (var j = 0; j < 24; j++) {
                var t0 = j * (Math.PI * 2 / 24)
                var len = (j % 3 === 0) ? 0.14 : 0.05
                ctx.beginPath()
                ctx.arc(0, 0, r * 0.71, t0, t0 + len)
                ctx.stroke()
            }
            ctx.restore()

            // Reactive audio waveform ticks around core when listening or speaking
            if (hudRoot.stateName === "listening" || hudRoot.stateName === "speaking") {
                var bars = 24
                var baseR = r * 0.62
                var amp = (hudRoot.stateName === "listening") ? Math.max(0.15, hudRoot.micLevel) : 0.45
                ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.8)
                ctx.lineWidth = 2.0
                for (var b = 0; b < bars; b++) {
                    var ba = b * (Math.PI * 2 / bars)
                    var wave = 0.5 + 0.5 * Math.sin(ba * 3 + hudRoot.outerAngle * 0.12)
                    var blen = r * (0.04 + 0.12 * amp * wave)
                    ctx.beginPath()
                    ctx.moveTo(cx + Math.cos(ba) * baseR, cy + Math.sin(ba) * baseR)
                    ctx.lineTo(cx + Math.cos(ba) * (baseR + blen), cy + Math.sin(ba) * (baseR + blen))
                    ctx.stroke()
                }
            }

            var levelBoost = (hudRoot.stateName === "listening") ? (hudRoot.micLevel * 0.08) : 0.0
            var coreR = r * (0.56 + levelBoost) * hudRoot.pulseScale
            ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.88)
            ctx.lineWidth = 2.0
            ctx.beginPath()
            ctx.arc(cx, cy, coreR, 0, Math.PI * 2)
            ctx.stroke()

            ctx.strokeStyle = Qt.rgba(0.85, 0.95, 1.0, 0.35)
            ctx.lineWidth = 1.2
            for (var k = 0; k < 4; k++) {
                var ang = k * Math.PI / 2
                ctx.beginPath()
                ctx.moveTo(cx + Math.cos(ang) * (r * 0.61), cy + Math.sin(ang) * (r * 0.61))
                ctx.lineTo(cx + Math.cos(ang) * (r * 0.67), cy + Math.sin(ang) * (r * 0.67))
                ctx.stroke()
            }
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 3

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "PRIME"
            color: "#E2F1FF"
            font.pixelSize: 19
            font.weight: Font.DemiBold
            font.letterSpacing: 5
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: {
                if (hudRoot.stateName === "listening") return "LISTENING"
                if (hudRoot.stateName === "transcribing") return "TRANSCRIBING"
                if (hudRoot.stateName === "thinking") return "THINKING"
                if (hudRoot.stateName === "speaking") return "SPEAKING"
                if (hudRoot.stateName === "error") return "ERROR"
                return "STANDBY • IDLE"
            }
            color: hudRoot.accentColor
            font.pixelSize: 10
            font.weight: Font.Medium
            font.letterSpacing: 1.8
        }
    }
}
