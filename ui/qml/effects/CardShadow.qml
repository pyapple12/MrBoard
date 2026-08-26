import QtQuick
import QtQuick.Effects

// MrBoard 卡片阴影/光晕封装（PL008.8.a）：MultiEffect 静态效果组件
// shadowEnabled 阴影 + blur 静态光晕（参数固定不动画，性能友好）；
// default property content 接收任意卡片内容（替代 1.6.7 缺失 FluCard 的阴影）；
// 内容区四周留白（卡片内缩）让阴影在 MultiEffect 边界内可见

Item {
    id: root
    default property alias content: contentItem.data
    property real shadowBlur: 0.5
    property real shadowVerticalOffset: 4
    property real shadowHorizontalOffset: 0
    property color shadowColor: "#40000000"
    property real blurAmount: 0.15

    // 内容层（MultiEffect 采样源；透明 Item 内含卡片，阴影基于卡片 alpha）
    Item {
        id: contentItem
        anchors.fill: parent
    }

    MultiEffect {
        id: effect
        objectName: "cardShadowEffect"
        anchors.fill: parent
        source: contentItem
        shadowEnabled: true
        shadowBlur: root.shadowBlur
        shadowVerticalOffset: root.shadowVerticalOffset
        shadowHorizontalOffset: root.shadowHorizontalOffset
        shadowColor: root.shadowColor
        blurEnabled: true
        blur: root.blurAmount
    }
}