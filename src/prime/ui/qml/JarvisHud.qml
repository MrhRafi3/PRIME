import QtQuick

Item {
    id: hudRoot
    property string stateName: "idle"
    property bool aiConnected: false

    readonly property color accentColor: {
        if (stateName === "listening") return "#22D3EE"
        if (stateName === "thinking") return "#F59E0B"
        if (stateName === "speaking") return "#F43F5E"
        return "#38BDF8"
    }
    readonly property color secondaryColor: stateName === "thinking" ? "#D97706" : "#1D4ED8"

    property real outerAngle: 0
    property real innerAngle: 0
    property real pulseScale: 1.0

    NumberAnimation on outerAngle {
        from: 0
        to: 360
        duration: hudRoot.stateName === "thinking" ? 5500 : 18000
        loops: Animation.Infinite
        running: hudRoot.visible
    }

    NumberAnimation on innerAngle {
        from: 360
        to: 0
        duration: hudRoot.stateName === "listening" ? 7000 : 14000
        loops: Animation.Infinite
        running: hudRoot.visible
    }

    SequentialAnimation on pulseScale {
        loops: Animation.Infinite
        running: hudRoot.visible
        NumberAnimation {
            from: 0.96
            to: hudRoot.stateName === "listening" ? 1.06 : 1.02
            duration: hudRoot.stateName === "listening" ? 900 : 2200
            easing.type: Easing.InOutSine
        }
        NumberAnimation {
            from: hudRoot.stateName === "listening" ? 1.06 : 1.02
            to: 0.96
            duration: hudRoot.stateName === "listening" ? 900 : 2200
            easing.type: Easing.InOutSine
        }
    }

    onOuterAngleChanged: hudCanvas.requestPaint()
    onInnerAngleChanged: hudCanvas.requestPaint()
    onStateNameChanged: hudCanvas.requestPaint()

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

            // Soft radial core ambient backdrop (restrained)
            var grad = ctx.createRadialGradient(cx, cy, r * 0.05, cx, cy, r * 1.05)
            grad.addColorStop(0.0, Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.22))
            grad.addColorStop(0.55, Qt.rgba(hudRoot.secondaryColor.r, hudRoot.secondaryColor.g, hudRoot.secondaryColor.b, 0.08))
            grad.addColorStop(1.0, "transparent")
            ctx.fillStyle = grad
            ctx.beginPath()
            ctx.arc(cx, cy, r * 1.05, 0, Math.PI * 2)
            ctx.fill()

            // Outer fine reference ring
            ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.22)
            ctx.lineWidth = 1.2
            ctx.beginPath()
            ctx.arc(cx, cy, r * 0.96, 0, Math.PI * 2)
            ctx.stroke()

            // Rotating segmented outer arcs
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

            // Counter-rotating dashed middle telemetry ring
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

            // Inner harmonic core ring
            var coreR = r * 0.56 * hudRoot.pulseScale
            ctx.strokeStyle = Qt.rgba(hudRoot.accentColor.r, hudRoot.accentColor.g, hudRoot.accentColor.b, 0.88)
            ctx.lineWidth = 2.0
            ctx.beginPath()
            ctx.arc(cx, cy, coreR, 0, Math.PI * 2)
            ctx.stroke()

            // Subtle cardinal ticks
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
                if (hudRoot.stateName === "thinking") return "PROCESSING"
                if (hudRoot.stateName === "speaking") return "SPEAKING"
                return "STANDBY • IDLE"
            }
            color: hudRoot.accentColor
            font.pixelSize: 10
            font.weight: Font.Medium
            font.letterSpacing: 1.8
        }
    }
}
