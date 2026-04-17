from app import app

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🧠 MemoMind - Bangla AI Assistant                       ║
    ║     =====================================                    ║
    ║                                                              ║
    ║     Server running at: http://localhost:5000                ║
    ║                                                              ║
    ║     Press CTRL+C to stop                                     ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)