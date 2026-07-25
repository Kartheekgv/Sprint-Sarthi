import {
  Bot,
  Check,
  ChevronDown,
  Cpu,
  Send,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import { useCallback, useRef, useState, type FormEvent } from 'react';
import { useOutsideClick } from '../../hooks/useOutsideClick';
import { askAssistant } from '../../services/mockApi';
import type { ChatMessage } from '../../types';
import { Panel } from '../common/Panel';
import { AIBrainIllustration } from '../common/DashboardIllustrations';

const models = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', label: 'Recommended' },
  { id: 'claude', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', label: 'Reasoning' },
  { id: 'gemini', name: 'Gemini 1.5 Pro', provider: 'Google', label: 'Long context' },
  { id: 'llama', name: 'Llama 3.1 70B', provider: 'Meta', label: 'Open source' },
];

const promptSuggestions = [
  'What should I de-scope?',
  'Summarise sprint risks',
  'Improve the sprint goal',
];

export function AICopilot() {
  const [selectedModel, setSelectedModel] = useState(models[0]);
  const [modelOpen, setModelOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'I reviewed the current plan. Capacity is healthy overall, but one backend dependency could affect the sprint goal.',
      timestamp: '09:42',
    },
  ]);
  const modelRef = useRef<HTMLDivElement>(null);
  const closeModels = useCallback(() => setModelOpen(false), []);
  useOutsideClick(modelRef, closeModels, modelOpen);

  const submitPrompt = async (event?: FormEvent<HTMLFormElement>, suggestedPrompt?: string) => {
    event?.preventDefault();
    const prompt = (suggestedPrompt ?? input).trim();
    if (!prompt || loading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      text: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);
    const reply = await askAssistant(prompt);
    setMessages((current) => [...current, reply]);
    setLoading(false);
  };

  return (
    <Panel
      className="ai-copilot"
      title="AI planning copilot"
      description="Ask focused questions using your sprint context."
      action={
        <span className="online-label">
          <span /> Online
        </span>
      }
    >
      <AIBrainIllustration className="ai-copilot__illustration" />
      <div className="model-picker" ref={modelRef}>
        <button className="model-picker__button" onClick={() => setModelOpen((current) => !current)}>
          <span className="model-picker__icon">
            <Cpu size={17} />
          </span>
          <span>
            <small>AI model</small>
            <strong>{selectedModel.name}</strong>
          </span>
          <span className="model-picker__provider">{selectedModel.provider}</span>
          <ChevronDown size={16} />
        </button>
        {modelOpen ? (
          <div className="model-menu">
            {models.map((model) => (
              <button
                key={model.id}
                className={model.id === selectedModel.id ? 'is-selected' : ''}
                onClick={() => {
                  setSelectedModel(model);
                  setModelOpen(false);
                }}
              >
                <span className="model-menu__icon">
                  <Bot size={16} />
                </span>
                <span>
                  <strong>{model.name}</strong>
                  <small>{model.provider}</small>
                </span>
                <em>{model.label}</em>
                {model.id === selectedModel.id ? <Check size={16} /> : null}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="chat-window">
        {messages.slice(-4).map((message) => (
          <div key={message.id} className={`chat-message chat-message--${message.role}`}>
            {message.role === 'assistant' ? (
              <span className="chat-message__avatar">
                <Sparkles size={15} />
              </span>
            ) : null}
            <div>
              <p>{message.text}</p>
              <time>{message.timestamp}</time>
            </div>
          </div>
        ))}
        {loading ? (
          <div className="chat-message chat-message--assistant">
            <span className="chat-message__avatar">
              <Sparkles size={15} />
            </span>
            <div className="typing-indicator" aria-label="Assistant is typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        ) : null}
      </div>

      <div className="prompt-suggestions">
        {promptSuggestions.map((prompt) => (
          <button key={prompt} onClick={() => void submitPrompt(undefined, prompt)}>
            <WandSparkles size={14} />
            {prompt}
          </button>
        ))}
      </div>

      <form className="chat-composer" onSubmit={(event) => void submitPrompt(event)}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about scope, capacity, risks..."
          aria-label="Message AI planning copilot"
        />
        <button type="submit" disabled={!input.trim() || loading} aria-label="Send message">
          <Send size={17} />
        </button>
      </form>
      <p className="ai-disclaimer">AI suggestions can be incorrect. Review decisions before changing sprint scope.</p>
    </Panel>
  );
}
