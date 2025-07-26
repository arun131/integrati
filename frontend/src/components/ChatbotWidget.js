import React, { useState } from 'react';
import api from '../services/api';

const LLM_OPTIONS = [
  { label: 'Gemini', value: 'gemini' },
  { label: 'OpenAI', value: 'openai' },
];

export default function ChatbotWidget({ token }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [llm, setLlm] = useState('gemini');

  const sendMessage = async () => {
    if (!input.trim()) return;
    setLoading(true);
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    try {
      const res = await api.post('/api/chatbot/message', { message: input, llm });
      setMessages(res.data.history || []);
    } catch (err) {
      console.error('Chatbot error:', err);
      setMessages([...newMessages, { role: 'assistant', content: 'Error: Could not get response.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{
      border: '1px solid #ccc', borderRadius: 8, padding: 16, maxWidth: 400, background: '#fafbfc',
      position: 'fixed', bottom: 32, right: 32, zIndex: 1000,
    }}>
      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <strong>Chatbot</strong>
        <select value={llm} onChange={e => setLlm(e.target.value)} style={{ fontSize: 12 }}>
          {LLM_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
      </div>
      <div style={{ height: 200, overflowY: 'auto', background: '#fff', border: '1px solid #eee', borderRadius: 4, padding: 8, marginBottom: 8 }}>
        {messages.length === 0 && <div style={{ color: '#aaa' }}>Ask me anything about your integrations!</div>}
        {messages.map((msg, i) => (
          <div key={i} style={{ margin: '8px 0', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
            <span style={{
              display: 'inline-block',
              background: msg.role === 'user' ? '#e3f2fd' : '#f1f8e9',
              color: '#333',
              borderRadius: 6,
              padding: '6px 12px',
              maxWidth: '80%',
              wordBreak: 'break-word',
            }}>{msg.content}</span>
          </div>
        ))}
        {loading && <div style={{ color: '#aaa' }}>Thinking...</div>}
      </div>
      <textarea
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={2}
        style={{ width: '100%', borderRadius: 4, border: '1px solid #ccc', padding: 8, resize: 'none', marginBottom: 8 }}
        placeholder="Type your message..."
        disabled={loading}
      />
      <button
        onClick={sendMessage}
        disabled={loading || !input.trim()}
        style={{ width: '100%', padding: 8, borderRadius: 4, background: '#1976d2', color: '#fff', border: 'none', fontWeight: 'bold', cursor: loading ? 'not-allowed' : 'pointer' }}
      >
        Send
      </button>
    </div>
  );
}
