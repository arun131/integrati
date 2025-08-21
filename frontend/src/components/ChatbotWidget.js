import React, { useState, useEffect } from 'react';
import { chatbotApi, tenantApi } from '../services/api';
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
  const [chatId, setChatId] = useState(null);
  const [tenantId, setTenantId] = useState(null);
  const [integrations, setIntegrations] = useState([]);

  // Debug: Monitor integrations state changes
  useEffect(() => {
    console.log('Integrations state changed:', integrations);
  }, [integrations]);

  // Initialize chat when component mounts
  useEffect(() => {
    if (token) {
      console.log('Token available, initializing chat...');
      initializeChat();
    }
  }, [token]);

  // Initialize chat and get available integrations
  const initializeChat = async () => {
    try {
      // Get tenant ID from localStorage or extract from token
      const storedTenantId = localStorage.getItem('tenant_id');
      if (!storedTenantId) {
        console.error('No tenant ID found');
        return;
      }
      setTenantId(storedTenantId);

      // Get user email from localStorage
      const userEmail = localStorage.getItem('user_email');
      if (!userEmail) {
        console.error('No user email found');
        return;
      }

      // Get available integrations using the token prop
      try {
        const availableIntegrations = [];

        // Check Gmail integration using tenantApi (same as DashboardPage)
        try {
          const gmailStatus = await tenantApi.getGmailStatus();
          if (gmailStatus && gmailStatus.status === 'connected') {
            availableIntegrations.push('gmail');
            console.log('Gmail integration connected');
          } else {
            console.log('Gmail integration not connected:', gmailStatus);
          }
        } catch (e) {
          console.log('Gmail not connected:', e);
        }

        // Check Calendar integration using tenantApi (same as DashboardPage)
        try {
          const calendarStatus = await tenantApi.getCalendarStatus();
          if (calendarStatus && calendarStatus.status === 'connected') {
            availableIntegrations.push('calendar');
            console.log('Calendar integration connected');
          } else {
            console.log('Calendar integration not connected:', calendarStatus);
          }
        } catch (e) {
          console.log('Calendar integration not connected:', e);
        }

        setIntegrations(availableIntegrations);
        console.log('Available integrations:', availableIntegrations);

        // Create new chat using chatbotApi
        const newChatResponse = await chatbotApi.createNewChat(
          userEmail,
          storedTenantId,
          availableIntegrations
        );

        if (newChatResponse.success) {
          setChatId(newChatResponse.chat_id);
          console.log('New chat created:', newChatResponse.chat_id);
        } else {
          console.error('Failed to create chat:', newChatResponse.error);
        }
      } catch (error) {
        console.error('Error getting integrations:', error);
        // Create chat with empty integrations if we can't get them
        const newChatResponse = await chatbotApi.createNewChat(
          userEmail,
          storedTenantId,
          []
        );

        if (newChatResponse.success) {
          setChatId(newChatResponse.chat_id);
        }
      }
    } catch (error) {
      console.error('Error initializing chat:', error);
    }
  };



  const sendMessage = async () => {
    if (!input.trim() || !chatId || !token) return;

    console.log('Sending message with integrations:', integrations);
    console.log('Current integrations state:', integrations);

    setLoading(true);
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    const userMessage = input;
    setInput('');

    try {
      // Send message using chatbotApi
      const res = await chatbotApi.sendMessage(
        chatId,
        userMessage,
        integrations,
        token
      );

      if (res.success) {
        // Add assistant response to messages
        const assistantMessage = {
          role: 'assistant',
          content: res.response,
          reasoning: res.reasoning,
          tools_used: res.tools_used
        };
        setMessages([...newMessages, assistantMessage]);
      } else {
        // Handle error response
        const errorMessage = {
          role: 'assistant',
          content: `Error: ${res.error || 'Unknown error occurred'}`,
          reasoning: res.reasoning || 'Error processing request'
        };
        setMessages([...newMessages, errorMessage]);
      }
    } catch (err) {
      console.error('Chatbot error:', err);
      const errorMessage = {
        role: 'assistant',
        content: 'Error: Could not get response. Please try again.',
        reasoning: 'Network or server error occurred'
      };
      setMessages([...newMessages, errorMessage]);
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

  // Don't render if no token or chat ID
  if (!token || !chatId) {
    return (
      <div style={{
        border: '1px solid #ccc', borderRadius: 8, padding: 16, maxWidth: 400, background: '#fafbfc',
        position: 'fixed', bottom: 32, right: 32, zIndex: 1000,
      }}>
        <div style={{ marginBottom: 8 }}>
          <strong>Chatbot</strong>
        </div>
        <div style={{ color: '#666', fontSize: '14px' }}>
          {!token ? 'Loading...' : 'Initializing chat...'}
        </div>
      </div>
    );
  }

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
            {msg.reasoning && (
              <div style={{ fontSize: '11px', color: '#666', marginTop: '4px', fontStyle: 'italic' }}>
                Reasoning: {msg.reasoning}
              </div>
            )}
            {msg.tools_used && msg.tools_used.length > 0 && (
              <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                Tools used: {msg.tools_used.join(', ')}
              </div>
            )}
          </div>
        ))}
        {loading && <div style={{ color: '#aaa' }}>Thinking...</div>}
      </div>

      {/* Available Agents Display */}
      <div style={{ marginBottom: 8, fontSize: '11px', color: '#666' }}>
        <div style={{ marginBottom: '4px' }}>Available Agents:</div>
        {integrations.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {integrations.map(integration => (
              <span
                key={integration}
                style={{
                  background: integration === 'gmail' ? '#4285f4' : '#34a853',
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '12px',
                  fontSize: '10px',
                  fontWeight: 'bold'
                }}
              >
                {integration === 'gmail' ? '📧 Gmail' : '📅 Calendar'}
              </span>
            ))}
          </div>
        ) : (
          <div style={{ color: '#999', fontStyle: 'italic' }}>No integrations connected</div>
        )}
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
