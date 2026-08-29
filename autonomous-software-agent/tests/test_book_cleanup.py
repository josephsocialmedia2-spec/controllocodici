from asa.book_pipeline import clean_faithful, clean_for_tts, recurring_headers


def test_cleanup_dehyphenates_and_removes_page_numbers():
    text = clean_faithful(["Questo è un pro-", "gramma.", "12"])
    assert "programma" in text
    assert "12" in text
    tts = clean_for_tts(text)
    assert "12" not in tts.splitlines()


def test_recurring_headers():
    pages = ["Titolo libro\nA", "Titolo libro\nB", "Titolo libro\nC"]
    assert "Titolo libro" in recurring_headers(pages)
