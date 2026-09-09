from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class AudioPlayer(QObject):
    state_changed = pyqtSignal(str) # 'playing', 'paused', 'stopped'
    position_changed = pyqtSignal(int, int) # current_ms, total_ms
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Default volume
        self.audio_output.setVolume(1.0) # 0.0 to 1.0

        # Connect signals
        self.player.playbackStateChanged.connect(self._handle_state_changed)
        self.player.positionChanged.connect(self._handle_position_changed)
        self.player.durationChanged.connect(self._handle_duration_changed)
        self.player.errorOccurred.connect(self._handle_error)

        self._duration = 0

    def load_and_play(self, file_path: str):
        # Stop current playback and clear media source to release file handle on Windows
        self.stop()
        self.player.setSource(QUrl())
        
        # Load new local file
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def set_volume(self, volume_percent: int):
        val = float(max(0, min(100, volume_percent))) / 100.0
        self.audio_output.setVolume(val)

    def set_position(self, position_ms: int):
        self.player.setPosition(position_ms)

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def _handle_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.state_changed.emit('playing')
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.state_changed.emit('paused')
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.state_changed.emit('stopped')

    def _handle_position_changed(self, position):
        self.position_changed.emit(position, self._duration)

    def _handle_duration_changed(self, duration):
        self._duration = duration
        self.position_changed.emit(self.player.position(), self._duration)

    def _handle_error(self, error, error_string):
        if error_string:
            self.error_occurred.emit(error_string)
