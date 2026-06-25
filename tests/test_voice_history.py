def test_voice_history_model_creation():
    from sqlalchemy_models import VoiceHistory, db
    # Test model can be imported and has expected fields
    assert hasattr(VoiceHistory, '__tablename__')
    assert VoiceHistory.__tablename__ == 'voice_history'
    # Check required fields exist
    assert hasattr(VoiceHistory, 'id')
    assert hasattr(VoiceHistory, 'entity_type')
    assert hasattr(VoiceHistory, 'entity_id')
    assert hasattr(VoiceHistory, 'audio_filename')
    assert hasattr(VoiceHistory, 'transcription')
    assert hasattr(VoiceHistory, 'created_at')