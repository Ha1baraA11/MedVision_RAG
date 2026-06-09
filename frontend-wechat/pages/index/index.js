// ========== 微信小程序主页 ==========
const app = getApp()
// API Host — 从配置文件加载候选地址，并行探测自动选择可用后端
const { API_CANDIDATES } = require('../../config');

// 新手引导教程步骤配置
var TUTORIAL_STEPS = [
    {
        id: 'upload', title: '拍照上传',
        desc: '点击中央蓝色按钮，拍照或上传图片/PDF/Word 文件以开始问诊',
        icon: 'camera', iconSrc: '/assets/camera.svg', phase: 'idle',
        tip: '上传成功后自动进入下一步',
        selector: '.camera-btn',
        cutoutPad: { top: 12, right: 12, bottom: 12, left: 12 }
    },
    {
        id: 'refresh', title: '刷新重置',
        desc: '点击右上角 ↻ 按钮可清空当前对话，回到拍照页面重新开始新的问诊',
        icon: 'refresh', iconText: '', phase: 'chat',
        tip: '教程期间不会真的重置',
        selector: '.reset-btn',
        cutoutPad: { top: 8, right: 8, bottom: 8, left: 8 }
    },
    {
        id: 'voice', title: '按住说话',
        desc: '按住底部绿色按钮开始语音提问，松开后自动发送并获取 AI 回复',
        icon: 'microphone', iconSrc: '/assets/microphone.svg', phase: 'chat',
        tip: '请按住绿色按钮说话，说完松开即可',
        selector: '.voice-btn',
        cutoutPad: { top: 8, right: 8, bottom: 8, left: 8 }
    },
    {
        id: 'tap-replay', title: '点击重播',
        desc: '收到 AI 回复后，点击消息文本即可让助手再次朗读，方便确认用药信息',
        icon: 'replay', iconText: '', phase: 'chat',
        tip: '点击 AI 回复文本即可重播语音',
        selector: '.ai-message',
        cutoutPad: { top: 8, right: 8, bottom: 8, left: 8 }
    }
];

/** 获取当前已探测到的后端 API 基础地址，未探测到时返回 null */
function getApiBase() {
  const host = app.globalData.discoveredHost;
  return host ? `${host}/api/medicine` : null;
}

Page({
    // ========== 页面数据 ==========
    data: {
        phase: 'idle',               // 当前页面阶段：'idle'=拍照页, 'chat'=对话页
        medicineName: '未知药品',     // 当前识别到的药品名称
        medicineId: null,            // 当前识别到的药品 ID
        chatHistory: [],             // 对话历史记录数组
        language: 'zh',              // 当前语言：'zh'=中文, 'en'=英文
        isListening: false,          // 是否正在录音
        isAutoListening: false,      // 是否为打断后自动触发的免按压录音
        isSpeaking: false,           // TTS 播放锁：播放时禁用麦克风
        isAnnouncingMedicine: false, // 药品名称播报锁
        isTranscribing: false,       // ASR 转写加载状态
        isThinking: false,           // AI 思考中状态
        isLoading: false,            // 全局加载状态
        statusMessage: '',           // 加载状态提示文案
        toView: '',                  // 滚动定位目标（用于自动滚到底部）
        recorderManager: null,       // 微信录音管理器实例
        innerAudioContext: null,     // 音频播放上下文
        showKeyboard: false,         // 是否显示键盘输入区域
        textInput: '',               // 文本输入框的值
        micIcon: '\uf130',
        pauseIcon: '\uf28b',

        // ========== 新手引导教程状态 ==========
        tutorialActive: false,       // 教程是否正在进行
        tutorialStep: 0,             // 当前教程步骤索引
        tutorialReady: false,        // 遮罩面板定位完成后才显示
        tutorialCompleted: false,    // 教程是否已完成（含历史记录）
        currentStepTitle: '',         // 当前教程步骤标题
        currentStepDesc: '',          // 当前教程步骤描述
        currentStepTip: '',           // 当前教程步骤提示
        currentStepIconSrc: '',       // 当前教程步骤图标路径
        currentStepIconText: '',      // 当前教程步骤图标文字
        currentStepCount: 4,          // 教程总步骤数
        panelTop: { height: 0 },     // 顶部遮罩面板样式
        panelBottom: { top: 0 },     // 底部遮罩面板样式
        panelLeft: { top: 0, width: 0, height: 0 },  // 左侧遮罩面板样式
        panelRight: { top: 0, left: 0, height: 0 },  // 右侧遮罩面板样式
        highlight: { top: 0, left: 0, width: 0, height: 0 }, // 高亮区域位置
        tooltipTop: '0px',            // 提示卡片顶部位置
        tooltipLeft: '0px',           // 提示卡片左侧位置
        windowHeight: 0,              // 窗口高度
        windowWidth: 0,               // 窗口宽度
    },

    /** 页面加载：初始化字体、录音管理器、权限检查、后端探测 */
    onLoad() {
        console.log('VERSION: UI_V7 (Probe):', API_CANDIDATES);

        // 加载 Font Awesome 字体（与 Web 端完全一致的图标）
        wx.loadFontFace({
            family: 'FontAwesome',
            source: 'url("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.woff2")',
            success: () => console.log('FontAwesome loaded'),
            fail: (err) => console.warn('FontAwesome load failed:', err)
        });

        // 显式关闭静音开关对语音播报的影响，避免真机上无声。
        wx.setInnerAudioOption({
            mixWithOther: false,
            obeyMuteSwitch: false,
            success: () => console.log('InnerAudio option configured'),
            fail: (err) => console.warn('InnerAudio option failed:', err)
        });

        // 1. 初始化录音管理器
        const rm = wx.getRecorderManager();
        // 录音停止后自动上传音频进行转写
        rm.onStop((res) => {
            this.uploadAudio(res.tempFilePath, res.duration || 0);
        });
        // 录音错误处理
        rm.onError((err) => {
            console.error('录音错误:', err);
            this.setData({
                isListening: false,
                isAutoListening: false,
                isLoading: false,
                isTranscribing: false
            });
            // 处理麦克风权限被拒绝的情况
            if (err.errMsg.includes('auth deny')) {
                wx.showModal({
                    title: '权限不足',
                    content: '请允许使用麦克风，否则无法语音对话',
                    confirmText: '去设置',
                    success: (res) => {
                        if (res.confirm) wx.openSetting();
                    }
                });
            } else {
                wx.showToast({ title: '录音失败', icon: 'none' });
            }
        });
        this.setData({ recorderManager: rm });

        // 2. 检查录音权限
        wx.getSetting({
            success(res) {
                if (!res.authSetting['scope.record']) {
                    wx.authorize({
                        scope: 'scope.record',
                        fail() {
                            console.warn('Auth Denied');
                        }
                    });
                }
            }
        });

        // 3. 并行探测所有候选地址，选择最快响应的后端
        this.probeBackend();
    },

    /** 并行探测所有候选后端地址，选择最快响应的作为 API Host */
    probeBackend() {
        if (this._backendReady) return; // 防止重复探测

        console.log('探测后端地址:', API_CANDIDATES);
        let found = false;

        // 并行发起健康检查请求，哪个先返回 200 就用哪个
        API_CANDIDATES.forEach((host) => {
            wx.request({
                url: `${host}/api/medicine/health`,
                method: 'GET',
                timeout: 3000,
                success: (res) => {
                    if (found) return;
                    if (res.statusCode === 200) {
                        found = true;
                        app.globalData.discoveredHost = host;
                        console.log('后端已连接:', host);
                        this._onBackendReady();
                    }
                },
                fail: () => {}
            });
        });

        // 全部候选地址失败时，8 秒后显示错误提示
        setTimeout(() => {
            if (!found) {
                console.error('所有候选地址均不可达');
                wx.showToast({
                    title: `无法连接后端 (共${API_CANDIDATES.length}个候选地址)`,
                    icon: 'none',
                    duration: 5000
                });
            }
        }, 8000);
    },

    /** 后端连接就绪后的回调：检查健康状态并播放欢迎语 */
    _onBackendReady() {
        if (this._backendReady) return;
        this._backendReady = true;

        const host = app.globalData.discoveredHost;
        console.log('使用 API 地址:', host);

        this.checkHealth();
        this.speak('欢迎使用，请拍照');
    },

    /** 检查后端健康状态 */
    checkHealth() {
        wx.request({
            url: `${getApiBase()}/health`,
            method: 'GET',
            success: (res) => {
                console.log('后端已连接:', res.statusCode);
            },
            fail: (err) => {
                console.error('后端连接失败:', err);
                wx.showToast({ title: '无法连接后端', icon: 'none' });
            }
        });
    },

    // ========== 拍照 / 文件上传 ==========
    /** 弹出操作菜单：选择拍照上传或从聊天记录选取文件 */
    triggerCamera() {
        wx.showActionSheet({
            itemList: ['上传照片', '从微信聊天记录选取文件'],
            success: (res) => {
                if (res.tapIndex === 0) {
                    this.chooseImage();
                } else if (res.tapIndex === 1) {
                    this.chooseFile();
                }
            }
        });
    },

    /** 从相机或相册选择图片 */
    chooseImage() {
        wx.chooseImage({
            count: 1,
            sizeType: ['compressed'],
            sourceType: ['camera', 'album'],
            success: (res) => {
                this.uploadImage(res.tempFilePaths[0]);
            }
        });
    },

    /** 从微信聊天记录中选取 PDF/Word 文件 */
    chooseFile() {
        wx.chooseMessageFile({
            count: 1,
            type: 'file',
            extension: ['pdf', 'doc', 'docx'],
            success: (res) => {
                const file = res.tempFiles[0];
                console.log('已选择文件:', file.name, file.size);
                this.uploadImage(file.path);
            },
            fail: (err) => {
                console.error('文件选择失败:', err);
            }
        });
    },

    /** 上传图片/文件到后端进行药品识别 */
    uploadImage(filePath) {
        this.setData({ isLoading: true, statusMessage: '识别中...' });
        this.speak('正在识别，请稍候。');
        console.log('上传文件:', filePath, '到', `${getApiBase()}/upload`);

        wx.uploadFile({
            url: `${getApiBase()}/upload`,
            filePath: filePath,
            name: 'file',
            success: (res) => {
                console.log('上传成功:', res);

                if (res.statusCode !== 200) {
                    console.error('服务端错误:', res.statusCode, res.data);
                        // 语音提示：识别出错
                    this.speak('抱歉，识别出错了。');
                    wx.showModal({
                        title: '服务端错误',
                        content: `状态码: ${res.statusCode}\n详情: ${res.data}`,
                        showCancel: false
                    });
                    return;
                }

                try {
                    const data = JSON.parse(res.data);
                    if (!data.id) throw new Error("无效响应：缺少药品 ID");

                    this.setData({
                        medicineId: data.id,
                        medicineName: data.name || '未知药品',
                        phase: 'chat',
                        isAnnouncingMedicine: true,
                        // 如果教程在 step 0，立刻隐藏旧面板防止残影
                        tutorialReady: this.data.tutorialActive && this.data.tutorialStep === 0 ? false : this.data.tutorialReady
                    });

                    // 教程：步骤0(上传) → 步骤1(刷新)，最短延迟等待 DOM 渲染
                    if (this.data.tutorialActive && this.data.tutorialStep === 0) {
                        var self = this;
                        setTimeout(function () { self.nextTutorialStep(); }, 80);
                    }

                    this.announceMedicine(`识别成功。是${data.name || '未知药品'}。请按住绿色按钮问我问题。`);
                } catch (e) {
                    console.error('JSON 解析错误:', e);
                    wx.showToast({ title: '数据解析失败', icon: 'none' });
                }
            },
            fail: (err) => {
                console.error('上传失败:', err);
                // 语音提示：识别出错
                this.speak('抱歉，识别出错了。');
                const errMsg = err.errMsg || '未知错误';
                if (errMsg.includes('ECONNREFUSED')) {
                    wx.showModal({
                        title: '连接失败',
                        content: '无法连接到后端服务(8080)。',
                        showCancel: false
                    });
                } else {
                    wx.showToast({ title: '识别失败', icon: 'none' });
                }
            },
            complete: () => {
                this.setData({ isLoading: false });
            }
        });
    },

    // ========== 语音识别（ASR） ==========
    /** 语音按钮触摸开始：检查状态后开始录音 */
    onVoiceTouchStart() {
        if (this.data.isAnnouncingMedicine || this.data.isSpeaking || this.data.isTranscribing || this.data.isThinking) {
            return;
        }
        this.startListening();
    },

    /** 语音按钮触摸结束：停止录音 */
    onVoiceTouchEnd() {
        this.stopListening();
    },

    /** 语音按钮点击事件：自动录音模式下点击停止 */
    onVoiceButtonTap() {
        if (this.data.isListening && this.data.isAutoListening) {
            this.stopListening();
        }
    },

    /** 开始录音：检查前置条件后启动微信录音管理器 */
    startListening() {
        // 未拍照时禁止语音输入
        if (this.data.phase === 'idle') {
            this.speak('请拍照。');
            return;
        }

        if (this.data.isSpeaking || this.data.isAnnouncingMedicine) {
            return;
        }

        if (this.data.chatHistory.length > 0) {
            this.stopSpeech();
        }

        if (this.data.isListening) {
            return;
        }

        // 教程：若教程在步骤2且已隐藏，用户重新录音时清除上一次的 TTS 等待标记
        if (this.data.tutorialStep === 2 && !this.data.tutorialCompleted) {
            this._tutorialWaitingForTts = false;
        }

        this.setData({ isListening: true });
        console.log('开始录音...');
        try {
            this.data.recorderManager.start({
                format: 'mp3'
            });
        } catch (e) {
            console.error(e);
            this.setData({ isListening: false, isAutoListening: false });
        }
    },

    /** 停止录音并触发转写 */
    stopListening() {
        if (!this.data.isListening) return;
        this.setData({
            isListening: false,
            isAutoListening: false,
            isTranscribing: true
        });
        console.log('停止录音...');
        this.data.recorderManager.stop();

        // 教程：步骤2松手后立即隐藏教程，等 AI 回复完再展示步骤3
        if (this.data.tutorialActive && this.data.tutorialStep === 2) {
            this.setData({ tutorialActive: false, tutorialReady: false });
        }
    },

    /** 打断当前 TTS 播报并自动进入录音状态 */
    interruptSpeech() {
        this.stopSpeech();
        this.setData({
            isSpeaking: false,
            isAnnouncingMedicine: false,
            isAutoListening: true
        });
        this.startListening();
    },

    /** 上传录音音频到后端进行 ASR 转写 */
    uploadAudio(filePath, duration) {
        if (duration < 500) { // 录音时长过短，提示用户
            this.setData({ isTranscribing: false });
            this.speak('请说长一点。');
            this._resumeTutorialStep2();
            return;
        }

        // 显示转写中状态（非全屏遮罩）
        this.setData({ isTranscribing: true });

        wx.uploadFile({
            url: `${getApiBase()}/transcribe`,
            filePath: filePath,
            name: 'file',
            success: (res) => {
                try {
                    const data = JSON.parse(res.data);
                    if (data.text && data.text.length > 0) {
                        this.handleUserQuestion(data.text);
                    } else {
                            // 语音提示：没听到
                        this.speak('抱歉，没听到什么。');
                        this._resumeTutorialStep2();
                    }
                } catch (e) {
                    console.error('ASR 转写解析错误:', e);
                    wx.showToast({ title: '转写解析失败', icon: 'none' });
                    this._resumeTutorialStep2();
                }
            },
            fail: (err) => {
                console.error(err);
                // 语音提示：没听清
                this.speak('抱歉，没听清。');
                this._resumeTutorialStep2();
            },
            complete: () => {
                this.setData({ isTranscribing: false });
            }
        });
    },

    // ========== 对话逻辑 ==========
    /** 处理用户提问：发送到后端获取 AI 回复，解析卡片数据 */
    handleUserQuestion(text) {
        const history = this.data.chatHistory;
        history.push({ role: 'user', content: text });
        this.setData({
            chatHistory: history,
            toView: 'scroll-bottom',
            isThinking: true // Show Thinking Pill
        });

        wx.request({
            url: `${getApiBase()}/chat`,
            method: 'POST',
            data: {
                medicineId: this.data.medicineId,
                question: text,
                language: this.data.language
            },
            success: (res) => {
                let answerText = res.data.answer;
                let cardData = null;

                const cardRegex = /<card>([\s\S]*?)<\/card>/;
                const match = answerText.match(cardRegex);

                if (match) {
                    try {
                        const jsonStr = match[1].replace(/```json/g, '').replace(/```/g, '').trim();
                        cardData = JSON.parse(jsonStr);
                        answerText = answerText.replace(match[0], "").trim();
                                        console.log('卡片数据已提取:', cardData);
                    } catch (e) {
                        console.error("Card Parse Error", e);
                    }
                }

                // 构造 AI 回复消息对象
                const aiMsg = {
                    role: 'ai',
                    content: answerText,
                    card: cardData
                };

                // 教程：步骤2(按住说话) → 等待 TTS 播完后再展示步骤3
                if (this.data.tutorialStep === 2 && !this.data.tutorialCompleted) {
                    this._tutorialWaitingForTts = true;
                }

                // TTS 音频下载完成后才显示文字+播放语音，期间保持"思考中"状态
                this.speak(answerText, () => {
                    const newHistory = this.data.chatHistory;
                    newHistory.push(aiMsg);
                    this.setData({
                        chatHistory: newHistory,
                        toView: 'scroll-bottom',
                        isThinking: false
                    });
                });
            },
            fail: (err) => {
                console.error(err);
                // 语音提示：网络错误
                this.speak('网络连接可能断开了。');
                this.setData({ isThinking: false });
            }
        });
    },

    // ========== 工具方法 ==========
    /** 点击 AI 回复文本触发 TTS 重播 */
    onAiTextTap(e) {
        // 教程：步骤3(点击重播) → 完成教程
        if (this.data.tutorialActive && this.data.tutorialStep === 3) {
            this.completeTutorial();
            return;
        }
        if (this.data.isSpeaking || this.data.isTranscribing ||
            this.data.isAnnouncingMedicine || this.data.isThinking) return;
        const index = e.currentTarget.dataset.index;
        const msg = this.data.chatHistory[index];
        if (!msg || !msg.content) return;
        this.speak(msg.content);
    },

    /** 切换键盘输入区域的显示/隐藏 */
    toggleDataInput() {
        this.setData({ showKeyboard: !this.data.showKeyboard });
    },

    /** 文本输入框内容变化事件 */
    onTextInput(e) {
        this.setData({ textInput: e.detail.value });
    },

    /** 发送文本输入的问题 */
    sendText() {
        const text = this.data.textInput.trim();
        if (!text) return;
        this.setData({ textInput: '', showKeyboard: false });
        this.handleUserQuestion(text);
    },

    /** 重置页面：清空对话历史，回到拍照页面 */
    reset() {
        // 教程：步骤1(刷新) 拦截，不执行真正的重置
        if (this.data.tutorialActive && this.data.tutorialStep === 1) {
            this.nextTutorialStep();
            return;
        }
        this.stopSpeech();
        this.setData({
            phase: 'idle',
            medicineName: '未知药品',
            chatHistory: [],
            isSpeaking: false,
            isAutoListening: false,
            isAnnouncingMedicine: false,
            isListening: false,
            isTranscribing: false,
            isThinking: false,
            isLoading: false,
            showKeyboard: false,
            textInput: ''
        });
    },

    /** 页面卸载时清理资源 */
    onUnload() {
        this.stopSpeech();
    },

    /** 停止当前 TTS 播放并清理音频资源 */
    stopSpeech() {
        // 先中止下载任务（若 abort() 异步触发 fail 回调，回调内会负责 destroy）
        const hadPendingDownload = !!this._ttsDownloadTask;
        if (this._ttsDownloadTask) {
            this._ttsDownloadTask.abort();
            this._ttsDownloadTask = null;
        }

        const currentAudio = this.data.innerAudioContext;
        this.setData({
            innerAudioContext: null,
            isSpeaking: false,
            isAnnouncingMedicine: false
        });

        if (!currentAudio) {
            return;
        }

        currentAudio.offCanplay();
        currentAudio.offPlay();
        currentAudio.offEnded();
        currentAudio.offError();
        currentAudio.stop();

        // 仅当没有待处理的下载回调时才在此销毁，避免双重 destroy
        if (!hadPendingDownload) {
            currentAudio.destroy();
        }
    },

    /** 播放普通语音（TTS） */
    speak(text, onReady) {
        if (!text) { if (onReady) onReady(); return; }
        this.playSpeech(text, 'isSpeaking', onReady);
    },

    /** 播放药品名称播报（使用 isAnnouncingMedicine 锁） */
    announceMedicine(text) {
        if (!text) return;
        this.playSpeech(text, 'isAnnouncingMedicine');
    },

    /** 核心 TTS 播放函数：下载后端音频 → 创建 InnerAudioContext → 播放 */
    playSpeech(text, speakingFlag, onReady) {
        console.log('播放语音（后端 TTS）:', text);
        this.stopSpeech();

        const audioUrl = `${getApiBase()}/tts?text=${encodeURIComponent(text)}`;
        const iac = wx.createInnerAudioContext();
        if (!iac) {
            wx.showToast({ title: '语音功能暂不可用', icon: 'none' });
            if (onReady) onReady();
            return;
        }
        iac.autoplay = false;
        iac.obeyMuteSwitch = false;

        const activeState = {
            innerAudioContext: iac,
            isSpeaking: speakingFlag === 'isSpeaking',
            isAnnouncingMedicine: speakingFlag === 'isAnnouncingMedicine'
        };
        const idleState = {
            innerAudioContext: null,
            isSpeaking: false,
            isAnnouncingMedicine: false
        };
        const requestId = (this._ttsRequestId || 0) + 1;
        this._ttsRequestId = requestId;

        this.setData(activeState);

        const safeDestroy = (audio) => {
            try { if (audio) audio.destroy(); } catch (e) { /* 已回收 */ }
        };

        iac.onPlay(() => {
            console.log(`音频播放中 -> ${speakingFlag}=true`);
            this.setData(activeState);
        });

        iac.onCanplay(() => {
            iac.play();
        });

        iac.onEnded(() => {
            console.log(`音频播放结束 -> ${speakingFlag}=false`);
            this.setData(idleState);
            safeDestroy(iac);

            // 教程：TTS 播完 → 重新展示教程并切到步骤3（点击重播）
            if (this._tutorialWaitingForTts) {
                this._tutorialWaitingForTts = false;
                var self = this;
                setTimeout(function () {
                    self.setData({ tutorialStep: 3, tutorialActive: true, tutorialReady: false });
                    setTimeout(function () { self._positionTutorial(); }, 400);
                }, 400);
            }
        });

        iac.onError((res) => {
            console.error('TTS 播放错误:', res);
            this.setData(idleState);
            safeDestroy(iac);

            // 教程：TTS 出错 → 同样推进步骤，不卡住
            if (this._tutorialWaitingForTts) {
                this._tutorialWaitingForTts = false;
                var self = this;
                setTimeout(function () {
                    self.setData({ tutorialStep: 3, tutorialActive: true, tutorialReady: false });
                    setTimeout(function () { self._positionTutorial(); }, 400);
                }, 400);
            }
        });

        this._ttsDownloadTask = wx.downloadFile({
            url: audioUrl,
            success: (res) => {
                this._ttsDownloadTask = null;

                if (requestId !== this._ttsRequestId) {
                    safeDestroy(iac);
                    return;
                }

                if (res.statusCode !== 200 || !res.tempFilePath) {
                    console.error('TTS 下载失败:', res);
                    if (onReady) onReady();
                    this.setData(idleState);
                    safeDestroy(iac);
                    wx.showToast({ title: '语音加载失败', icon: 'none' });
                    return;
                }

                console.log('TTS 下载成功:', res.tempFilePath);
                if (onReady) onReady();
                iac.src = res.tempFilePath;
            },
            fail: (err) => {
                this._ttsDownloadTask = null;

                if (requestId !== this._ttsRequestId) {
                    safeDestroy(iac);
                    return;
                }

                console.error('TTS 下载错误:', err);
                if (onReady) onReady();
                this.setData(idleState);
                safeDestroy(iac);
                wx.showToast({ title: '语音下载失败', icon: 'none' });
            }
        });

        this.setData({ innerAudioContext: iac });
    },

    // ========== 新手引导教程方法 ==========

    /** 页面渲染完成：初始化教程 */
    onReady: function () {
        this.initTutorial();
    },

    /** 窗口尺寸变化时重新计算教程定位 */
    onResize: function () {
        if (this.data.tutorialActive) {
            var sysInfo = wx.getSystemInfoSync();
            this.setData({ windowHeight: sysInfo.windowHeight, windowWidth: sysInfo.windowWidth });
            if (this.data.tutorialReady) this._positionTutorial();
        }
    },

    /** 初始化教程：检查是否已完成，未完成则启动引导 */
    initTutorial: function () {
        try {
            if (wx.getStorageSync('medvision_onboarded') === '1') {
                this.setData({ tutorialCompleted: true });
                return;
            }
        } catch (e) { /* ignore */ }
        var sysInfo = wx.getSystemInfoSync();
        this.setData({
            tutorialActive: true,
            tutorialStep: 0,
            windowHeight: sysInfo.windowHeight,
            windowWidth: sysInfo.windowWidth
        });
        var self = this;
        setTimeout(function () { self._positionTutorial(); }, 400);
    },

    /** 定位教程高亮区域：查询目标元素位置并计算遮罩面板 */
    _positionTutorial: function () {
        var step = TUTORIAL_STEPS[this.data.tutorialStep];
        if (!step) return;
        var self = this;
        var query = wx.createSelectorQuery().in(this);
        if (step.selector === '.reset-btn' || step.selector === '.ai-message') {
            query.selectAll(step.selector).boundingClientRect();
        } else {
            query.select(step.selector).boundingClientRect();
        }
        query.exec(function (res) {
            var rect;
            if (Array.isArray(res[0])) {
                rect = res[0][res[0].length - 1];
            } else {
                rect = res[0];
            }
            if (!rect || rect.width === 0 || rect.height === 0) {
                if (!self._tutorialRetried) {
                    self._tutorialRetried = true;
                    setTimeout(function () { self._tutorialRetried = false; self._positionTutorial(); }, 500);
                } else {
                    self._tutorialRetried = false;
                    setTimeout(function () { self.nextTutorialStep(); }, 800);
                }
                return;
            }
            self._tutorialRetried = false;
            self._applyTutorialPositions(rect, step);
        });
    },

    /** 应用教程定位：设置遮罩面板和提示卡片的位置 */
    _applyTutorialPositions: function (rect, step) {
        var winH = this.data.windowHeight;
        var winW = this.data.windowWidth;
        var pad = step.cutoutPad || { top: 8, right: 8, bottom: 8, left: 8 };
        var ct = Math.max(0, rect.top - pad.top);
        var cl = Math.max(0, rect.left - pad.left);
        var cb = Math.min(winH, rect.bottom + pad.bottom);
        var cr = Math.min(winW, rect.right + pad.right);
        var tooltipW = 320;
        var tooltipHest = 260;
        var gap = 16;
        var tipTop = cb + gap;
        var tipLeft = rect.left + rect.width / 2 - tooltipW / 2;
        if (tipTop + tooltipHest > winH) {
            tipTop = rect.top - pad.top - gap - tooltipHest;
            tipTop = Math.max(8, tipTop);
        }
        var maxLeft = winW - tooltipW - 16;
        tipLeft = Math.max(16, Math.min(maxLeft, tipLeft));
        this.setData({
            currentStepTitle: step.title,
            currentStepDesc: step.desc,
            currentStepTip: step.tip,
            currentStepIconSrc: step.iconSrc || '',
            currentStepIconText: step.iconText || '',
            highlight: { top: ct, left: cl, width: cr - cl, height: cb - ct },
            panelTop: { height: ct },
            panelBottom: { top: cb },
            panelLeft: { top: ct, width: cl, height: cb - ct },
            panelRight: { top: ct, left: cr, height: cb - ct },
            tooltipTop: tipTop + 'px',
            tooltipLeft: tipLeft + 'px',
            tutorialReady: true
        });
    },

    /** 推进到教程的下一步 */
    nextTutorialStep: function () {
        if (this.data.tutorialStep >= TUTORIAL_STEPS.length - 1) {
            this.completeTutorial();
            return;
        }
        var nextStep = this.data.tutorialStep + 1;
        this.setData({ tutorialStep: nextStep, tutorialReady: false });
        var self = this;
        setTimeout(function () { self._positionTutorial(); }, 120);
    },

    /** 完成教程并持久化标记到本地存储 */
    completeTutorial: function () {
        this.setData({ tutorialActive: false, tutorialCompleted: true, tutorialReady: false });
        try { wx.setStorageSync('medvision_onboarded', '1'); } catch (e) { /* ignore */ }
    },

    /** 跳过教程 */
    skipTutorial: function () { this.completeTutorial(); },

    /** 若教程在步骤2且因松手被隐藏，录音/转写失败时恢复展示 */
    _resumeTutorialStep2: function () {
        if (this.data.tutorialStep === 2 && !this.data.tutorialCompleted && !this.data.tutorialActive) {
            this.setData({ tutorialActive: true, tutorialReady: false });
            var self = this;
            setTimeout(function () { self._positionTutorial(); }, 400);
        }
    },
    /** 教程遮罩面板点击事件（阻止穿透） */
    onTutorialPanelTap: function () { /* 吸收点击事件，防止穿透到下层 */ },
    /** 教程提示卡片点击事件（阻止穿透） */
    onTutorialTooltipTap: function () { /* 吸收点击事件，防止穿透到下层 */ },
})
