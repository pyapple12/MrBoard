import QtQuick
import QtQuick.Controls
import FluentUI
import "theme"

// MrBoard QML 前端骨架（PL008.5.a）：FluWindow 根 + FluNavigationView 两页导航
// 页面为占位组件（PL008.6 用量监控 / PL008.7 数据与动态 填充）；
// 无头探针经本文件暴露的验证属性读取导航与主题状态

FluWindow {
    id: window
    width: 960
    height: 640
    title: "MrBoard"

    // 验证/调试用暴露属性（.temp/probe_qml_skeleton.py 无头读取）
    property int navCount: navView.items ? navView.items.children.length : 0
    property string navTitle1: navView.items && navView.items.children.length > 0 ? navView.items.children[0].title : ""
    property string navTitle2: navView.items && navView.items.children.length > 1 ? navView.items.children[1].title : ""
    property int currentIndex: 0
    property string themeChunkOk: Theme.chunkOk
    property string themeChunkWarn: Theme.chunkWarn
    property string themeChunkDanger: Theme.chunkDanger
    property string themePie1: Theme.pie1
    property string themeName: Theme.themeName
    property bool themeReducedMotion: Theme.reducedMotion
    property string themeBorderSubtle: Theme.borderSubtle
    property string themeRowStripe: Theme.rowStripe
    property int themeRadius: Theme.radius

    // 页面组件（PL008.6 用量监控页已实现；PL008.7 数据与动态页为占位）
    FluNavigationView {
        id: navView
        objectName: "navView"
        anchors.fill: parent
        title: "MrBoard"
        // NoStack 模式：切换时销毁旧页重建新页（官方推荐，内存占用少）
        pageMode: FluNavigationViewType.NoStack
        items: FluObject {
            id: navItems
            // 页面加载由各 FluPaneItem.onTap 显式调用 push（FluNavigationView
            // 不自动加载页面——官方 demo 模式）
            property var navigationView: null
            FluPaneItem {
                title: "用量监控"
                icon: 0xE9D2
                url: Qt.resolvedUrl("UsagePage.qml")
                onTap: {
                    navItems.navigationView.push(url)
                }
            }
            FluPaneItem {
                title: "数据与动态"
                icon: 0xE81C
                url: Qt.resolvedUrl("DataPage.qml")
                onTap: {
                    navItems.navigationView.push(url)
                }
            }
        }
        // 启动即展示第一页：先绑定 navigationView 引用，再激活索引触发 onTap
        Component.onCompleted: {
            navItems.navigationView = navView
            setCurrentIndex(0)
        }
    }

    // 切换第二页并同步 currentIndex（探针经 QMetaObject.invokeMethod 调用）
    function switchToSecond() {
        navView.setCurrentIndex(1)
        currentIndex = navView.getCurrentIndex()
    }
}