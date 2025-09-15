import React, { useState, useEffect } from 'react';
// Lucide React icons for a modern, clean look
import { Home, Settings, Plug, User, Send, Mail, Camera, ListTodo, Newspaper, ArrowRight, ChevronDown, FileText, X, Calendar, Eye, Target, Zap, Mic } from 'lucide-react';

// Persona type definitions
type PersonaType = 'byakugan' | 'sharingan' | 'rinnegan';

// Persona configurations with themes based on the provided image
const personaConfig = {
    byakugan: {
        name: 'The Byakugan',
        description: 'Stoic and watchful observer with unshakeable clarity',
        icon: Eye,
        theme: {
            primary: 'from-slate-600 to-indigo-800',
            accent: 'slate-700',
            background: 'bg-slate-900',
            card: 'bg-slate-800/90 border-slate-600/50 backdrop-blur-sm',
            cardSolid: 'bg-slate-800 border-slate-600',
            text: 'text-white',
            textSecondary: 'text-slate-200',
            textMuted: 'text-slate-300',
            button: 'bg-slate-700 hover:bg-slate-600 text-white',
            buttonSecondary: 'bg-slate-700/40 text-white border-slate-600 hover:bg-slate-600/40',
            nav: 'bg-slate-800/90 text-white',
            gradient: 'bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900',
            notification: 'bg-slate-800 border-slate-600 text-white',
            surface: 'bg-slate-800/60',
            border: 'border-slate-600'
        },
        tone: {
            greeting: 'I observe all with clarity.',
            taskComplete: 'Task completed with precision.',
            error: 'I detect an anomaly that requires attention.',
            guidance: 'Allow me to guide you with clear sight.'
        }
    },
    sharingan: {
        name: 'The Sharingan',
        description: 'Charismatic prodigy who learns and adapts rapidly',
        icon: Target,
        theme: {
            primary: 'from-red-600 to-orange-600',
            accent: 'red-700',
            background: 'bg-red-950',
            card: 'bg-red-900/90 border-red-700/50 backdrop-blur-sm',
            cardSolid: 'bg-red-900 border-red-700',
            text: 'text-white',
            textSecondary: 'text-red-100',
            textMuted: 'text-red-200',
            button: 'bg-red-700 hover:bg-red-600 text-white',
            buttonSecondary: 'bg-red-800/40 text-white border-red-700 hover:bg-red-700/40',
            nav: 'bg-red-900/90 text-white',
            gradient: 'bg-gradient-to-br from-red-950 via-red-900 to-orange-950',
            notification: 'bg-red-900 border-red-700 text-white',
            surface: 'bg-red-900/60',
            border: 'border-red-700'
        },
        tone: {
            greeting: 'I anticipate your every need.',
            taskComplete: 'Another technique mastered.',
            error: 'An illusion? Let me see through this.',
            guidance: 'Watch and learn as I demonstrate.'
        }
    },
    rinnegan: {
        name: 'The Rinnegan',
        description: 'Ancient deity with cosmic understanding and immense power',
        icon: Zap,
        theme: {
            primary: 'from-purple-600 to-violet-800',
            accent: 'purple-700',
            background: 'bg-purple-950',
            card: 'bg-purple-900/90 border-purple-700/50 backdrop-blur-sm',
            cardSolid: 'bg-purple-900 border-purple-700',
            text: 'text-white',
            textSecondary: 'text-purple-100',
            textMuted: 'text-purple-200',
            button: 'bg-purple-700 hover:bg-purple-600 text-white',
            buttonSecondary: 'bg-purple-800/40 text-white border-purple-700 hover:bg-purple-700/40',
            nav: 'bg-purple-900/90 text-white',
            gradient: 'bg-gradient-to-br from-purple-950 via-purple-900 to-violet-950',
            notification: 'bg-purple-900 border-purple-700 text-white',
            surface: 'bg-purple-900/60',
            border: 'border-purple-700'
        },
        tone: {
            greeting: 'The cycles of existence flow through me.',
            taskComplete: 'Balance has been restored.',
            error: 'I sense a disturbance in the natural order.',
            guidance: 'Let me share the wisdom of ages.'
        }
    }
};

// Main App component
const App = () => {
    // State to manage which page is currently active
    const [activePage, setActivePage] = useState('dashboard');
    // Persona state management
    const [selectedPersona, setSelectedPersona] = useState<PersonaType | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(true);
    // State for managing tasks
    const [tasks, setTasks] = useState([
        { id: 1, title: 'TD Insurance Claim', subtitle: "I've filled the application form. You can review and submit.", status: 'review', icon: FileText },
        { id: 2, title: 'Respond to HR on benefits', subtitle: "I drafted the email but could you add the missing benefits id and reply to HR.", status: 'review', icon: Mail },
        { id: 3, title: 'Weekend meeting', subtitle: "Added a meeting on your calendar for the weekend event.", status: 'review', icon: Calendar }
    ]);
    // State to switch between main view and the TD form view
    const [currentScreen, setCurrentScreen] = useState('main');
    // State for overlays on the Integrations page
    const [showAddIntegrations, setShowAddIntegrations] = useState(false);
    const [selectedExternal, setSelectedExternal] = useState(null as null | 'Gemini' | 'Claude');
    // Simulated notification and approval panel for Claude email
    const [showClaudeNotif, setShowClaudeNotif] = useState(true);
    const [showClaudeEmailPanel, setShowClaudeEmailPanel] = useState(false);
    // State for simulated webpage
    const [showWebpage, setShowWebpage] = useState(false);
    const [webpageMessage, setWebpageMessage] = useState('');
    // State for feed items (to handle dismissals)
    const [feedItems, setFeedItems] = useState([
        { id: 1, icon: User, message: "Michael got promoted to Lead data scientist. He just posted on linkedin" },
        { id: 2, icon: Newspaper, message: "Elon Musk says Optimus will be the best product ever in the All-in-Podcast summit." },
        { id: 3, icon: Mail, message: "The Best Buy offer of 10% off on new phones ends in 2 days." }
    ]);
    // State for text input visibility
    const [showTextInput, setShowTextInput] = useState(false);

    // Load saved persona from localStorage
    useEffect(() => {
        const savedPersona = localStorage.getItem('selectedPersona') as PersonaType;
        if (savedPersona && personaConfig[savedPersona]) {
            setSelectedPersona(savedPersona);
            setShowOnboarding(false);
        }
    }, []);

    // Save persona to localStorage
    const handlePersonaSelect = (persona: PersonaType) => {
        setSelectedPersona(persona);
        setShowOnboarding(false);
        localStorage.setItem('selectedPersona', persona);
    };

    // Get current theme
    const currentTheme = selectedPersona ? personaConfig[selectedPersona].theme : personaConfig.byakugan.theme;
    const currentTone = selectedPersona ? personaConfig[selectedPersona].tone : personaConfig.byakugan.tone;

    const handleTaskSubmit = (taskId: number) => {
        setTasks(currentTasks =>
            currentTasks.map(task =>
                task.id === taskId ? { ...task, status: 'done' } : task
            )
        );
        setCurrentScreen('main'); // Go back to the main view
    };

    // Handler for opening simulated webpage
    const handleOpenWebpage = (message: string) => {
        setWebpageMessage(message);
        setShowWebpage(true);
    };

    // Handler for dismissing feed items
    const handleDismissFeedItem = (itemId: number) => {
        setFeedItems(currentItems =>
            currentItems.filter(item => item.id !== itemId)
        );
    };

    // Header component for the top of the mobile screen
    const Header = ({ userEmail }: { userEmail: string }) => {
        const [showNotifications, setShowNotifications] = useState(false);
        const notificationCount = showClaudeNotif ? 1 : 0;

        return (
            <header className={`backdrop-blur-lg p-4 border-b flex items-center justify-between sticky top-0 z-10 ${currentTheme.cardSolid} ${currentTheme.border}`}>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowTextInput(!showTextInput)}
                        className="flex items-center gap-3 hover:opacity-80 transition-opacity"
                    >
                        <h1 className={`text-xl font-bold ${currentTheme.text}`}>Integrati</h1>
                        {selectedPersona && (
                            <div className={`bg-gradient-to-r ${currentTheme.primary} p-1 rounded-full`}>
                                {React.createElement(personaConfig[selectedPersona].icon, {
                                    className: "w-4 h-4 text-white"
                                })}
                            </div>
                        )}
                    </button>
                </div>

                <div className="flex items-center gap-3">
                    {/* Notifications */}
                    <div className="relative">
                        <button
                            onClick={() => setShowNotifications(!showNotifications)}
                            className={`relative p-2 rounded-full hover:opacity-80 transition-opacity ${currentTheme.buttonSecondary}`}
                        >
                            <Mail className={`w-5 h-5 ${currentTheme.text}`} />
                            {notificationCount > 0 && (
                                <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                                    {notificationCount}
                                </div>
                            )}
                        </button>

                        {/* Notification Dropdown */}
                        {showNotifications && showClaudeNotif && (
                            <div className={`absolute right-0 top-full mt-2 w-80 rounded-lg shadow-lg border z-20 ${currentTheme.cardSolid} ${currentTheme.border}`}>
                                <div className={`p-3 border-b ${currentTheme.border}`}>
                                    <p className={`text-sm font-medium ${currentTheme.text}`}>
                                        Claude requests approval to send an email
                                    </p>
                                </div>
                                <div className="p-3 flex gap-2">
                                    <button
                                        onClick={() => { setShowNotifications(false); setShowClaudeEmailPanel(true); }}
                                        className={`px-3 py-1.5 text-sm font-medium text-white rounded-md hover:opacity-90 transition-opacity ${currentTheme.button}`}
                                    >
                                        Review
                                    </button>
                                    <button
                                        onClick={() => { setShowClaudeNotif(false); setShowNotifications(false); }}
                                        className={`px-3 py-1.5 text-sm font-medium rounded-md border hover:opacity-80 transition-opacity ${currentTheme.buttonSecondary} ${currentTheme.border}`}
                                    >
                                        Dismiss
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* User Avatar */}
                    <div className={`p-2 rounded-full ${currentTheme.buttonSecondary}`}>
                        <User className={`w-5 h-5 ${currentTheme.text}`} />
                    </div>
                </div>
            </header>
        );
    };

    // Bottom Navigation component, a staple of mobile UIs
    const BottomNav = ({ activePage, setActivePage }: { activePage: string, setActivePage: (page: string) => void }) => (
        <nav className={`backdrop-blur-lg border-t p-2 flex justify-around items-center sticky bottom-0 z-10 ${currentTheme.cardSolid} ${currentTheme.border}`}>
            <button
                onClick={() => setActivePage('dashboard')}
                className={`flex flex-col items-center justify-center w-full py-2 rounded-lg transition-colors duration-200 ${
                    activePage === 'dashboard' ? currentTheme.nav : `${currentTheme.textSecondary} hover:${currentTheme.buttonSecondary}`
                }`}
            >
                <Home className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">Home</span>
            </button>
            <button
                onClick={() => setActivePage('integrations')}
                className={`flex flex-col items-center justify-center w-full py-2 rounded-lg transition-colors duration-200 ${
                    activePage === 'integrations' ? currentTheme.nav : `${currentTheme.textSecondary} hover:${currentTheme.buttonSecondary}`
                }`}
            >
                <Plug className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">Integrations</span>
            </button>
            <button
                onClick={() => setActivePage('done')}
                className={`flex flex-col items-center justify-center w-full py-2 rounded-lg transition-colors duration-200 ${
                    activePage === 'done' ? currentTheme.nav : `${currentTheme.textSecondary} hover:${currentTheme.buttonSecondary}`
                }`}
            >
                <ListTodo className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">Done</span>
            </button>
            <button
                onClick={() => setActivePage('settings')}
                className={`flex flex-col items-center justify-center w-full py-2 rounded-lg transition-colors duration-200 ${
                    activePage === 'settings' ? currentTheme.nav : `${currentTheme.textSecondary} hover:${currentTheme.buttonSecondary}`
                }`}
            >
                <Settings className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">Settings</span>
            </button>
        </nav>
    );

    // Card component adapted for mobile view
    const Card = ({ title, children, className = '', noPadding = false, solid = false, style = {} }: { title?: string, children: React.ReactNode, className?: string, noPadding?: boolean, solid?: boolean, style?: React.CSSProperties }) => {
        return (
            <div className={`rounded-xl shadow-sm border ${className} ${currentTheme.cardSolid} ${currentTheme.border}`} style={style}>
                {title && <h2 className={`text-lg font-semibold p-4 border-b ${currentTheme.text} ${currentTheme.border}`}>{title}</h2>}
                <div className={noPadding ? '' : 'p-4'}>
                    {children}
                </div>
            </div>
        );
    };

    // Persona Selection Onboarding Component
    const PersonaOnboarding = () => (
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 z-50 flex flex-col items-center justify-center p-6">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-white mb-4">Choose Your Partner</h1>
                <p className="text-slate-300 text-lg">Select a persona that will guide your Integrati experience</p>
            </div>

            <div className="space-y-4 w-full max-w-sm">
                {(Object.keys(personaConfig) as PersonaType[]).map((persona) => {
                    const config = personaConfig[persona];
                    const IconComponent = config.icon;

                    return (
                        <button
                            key={persona}
                            onClick={() => handlePersonaSelect(persona)}
                            className="w-full group relative overflow-hidden rounded-2xl p-6 transition-all duration-300 hover:scale-105 hover:shadow-2xl"
                            style={{
                                background: `linear-gradient(135deg, ${
                                    persona === 'byakugan' ? '#3b82f6, #8b5cf6' :
                                    persona === 'sharingan' ? '#ef4444, #f97316' :
                                    '#8b5cf6, #ec4899'
                                })`
                            }}
                        >
                            <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-colors duration-300" />
                            <div className="relative flex items-center gap-4">
                                <div className="flex-shrink-0 ${currentTheme.cardSolid}/20 backdrop-blur-sm p-3 rounded-full">
                                    <IconComponent className="w-8 h-8 text-white" />
                                </div>
                                <div className="text-left">
                                    <h3 className="text-xl font-bold text-white mb-1">{config.name}</h3>
                                    <p className="text-white/80 text-sm">{config.description}</p>
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>

            <div className="mt-8 text-center">
                <p className="text-slate-400 text-sm">You can change this later in Settings</p>
            </div>
        </div>
    );

    // TD Insurance Claim Form component
    const TdClaimForm = ({ task, onSubmit }: { task: any, onSubmit: (taskId: number) => void }) => (
        <div className={`absolute inset-0 ${currentTheme.background} z-20 flex flex-col`}>
            <header className={`${currentTheme.cardSolid} p-4 ${currentTheme.border} border-b flex items-center justify-between sticky top-0`}>
                <h1 className={`text-lg font-bold ${currentTheme.text}`}>Review TD Claim</h1>
                <button onClick={() => setCurrentScreen('main')} className={`p-2 rounded-full ${currentTheme.buttonSecondary}`}>
                    <X className={`w-5 h-5 ${currentTheme.textSecondary}`} />
                </button>
            </header>
            <div className="flex-grow p-4 overflow-y-auto">
                <Card title="Auto Insurance Claim Details">
                    <form className="space-y-4">
                        <div>
                            <label className={`block text-sm font-medium ${currentTheme.text}`}>Policy Number</label>
                            <input type="text" value="123-456-789" readOnly className={`mt-1 block w-full ${currentTheme.buttonSecondary} border-gray-300 rounded-md shadow-sm p-2`} />
                        </div>
                        <div>
                            <label className="block text-sm font-medium ${currentTheme.text}">Claimant Name</label>
                            <input type="text" value="Arun Raj" readOnly className="mt-1 block w-full ${currentTheme.buttonSecondary} border-gray-300 rounded-md shadow-sm p-2" />
                        </div>
                         <div>
                            <label className="block text-sm font-medium ${currentTheme.text}">Date of Incident</label>
                            <input type="text" value="2025-09-10" readOnly className="mt-1 block w-full ${currentTheme.buttonSecondary} border-gray-300 rounded-md shadow-sm p-2" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium ${currentTheme.text}">Description</label>
                            <textarea rows={4} readOnly className="mt-1 block w-full ${currentTheme.buttonSecondary} border-gray-300 rounded-md shadow-sm p-2" value="Minor fender bender in the parking lot. No injuries reported."></textarea>
                        </div>
                    </form>
                </Card>
            </div>
            <div className="p-4 ${currentTheme.cardSolid} border-t ${currentTheme.border}">
                <button onClick={() => onSubmit(task.id)} className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                    Submit Claim
                </button>
            </div>
        </div>
    );

    // Task Item component
    const TaskItem = ({ task, onReview, onSubmit }: { task: any, onReview: () => void, onSubmit: (taskId: number) => void }) => {
        const [isExpanded, setIsExpanded] = useState(false);
        const [isModifying, setIsModifying] = useState(false);
        const [showSubmittedMsg, setShowSubmittedMsg] = useState(false);
        const Icon = task.icon;

        const handleSubmitClick = () => {
            setShowSubmittedMsg(true);
            setTimeout(() => {
                onSubmit(task.id);
                 setShowSubmittedMsg(false);
            }, 1500); // Wait 1.5 seconds before moving the task
        };

        if (showSubmittedMsg) {
            return (
                <div className={`p-4 text-center font-medium flex items-center justify-center gap-2`} style={{ color: currentTheme.accent }}>
                    {selectedPersona && React.createElement(personaConfig[selectedPersona].icon, {
                        className: "w-5 h-5"
                    })}
                    <span>{currentTone.taskComplete}</span>
                </div>
            );
        }

        return (
            <div className={`p-4 border-b last:border-b-0 cursor-pointer ${currentTheme.border}`} onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex items-start gap-3">
                    {/* Status indicator */}
                    <div className="flex-shrink-0 mt-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>

                    {/* Content */}
                    <div className="flex-grow">
                        <h4 className={`font-medium text-sm mb-1 ${currentTheme.text}`}>
                            {task.title}
                        </h4>
                        <p className={`text-sm leading-relaxed ${currentTheme.textSecondary}`}>
                            {task.subtitle}
                        </p>

                        {/* Action buttons - only show when expanded */}
                        {isExpanded && (
                            <div className="flex items-center gap-2 mt-3">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onReview();
                                    }}
                                    className={`px-3 py-1.5 text-xs font-medium text-white rounded-md hover:opacity-90 transition-opacity ${currentTheme.button}`}
                                >
                                    Review
                                </button>
                                <button
                                    onClick={(e) => e.stopPropagation()}
                                    className={`px-3 py-1.5 text-xs font-medium rounded-md border hover:opacity-80 transition-opacity ${currentTheme.buttonSecondary} ${currentTheme.border}`}
                                >
                                    Modify
                                </button>
                                <button
                                    onClick={(e) => e.stopPropagation()}
                                    className={`px-3 py-1.5 text-xs font-medium rounded-md border hover:opacity-80 transition-opacity ${currentTheme.buttonSecondary} ${currentTheme.border}`}
                                >
                                    Dismiss
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // Email Approval Panel (Claude)
    const EmailApprovalPanel = ({ onClose }: { onClose: () => void }) => {
        const [to, setTo] = useState('michael@example.com');
        const [subject, setSubject] = useState('Congratulations on your promotion!');
        const [body, setBody] = useState(
            'Hi Michael,\n\nCongratulations on your promotion to Lead Data Scientist!\nWishing you great success in the new role.\n\nBest,\nArun'
        );

        const handleApprove = () => {
            // Simulate sending...
            onClose();
        };
        const handleReject = () => {
            onClose();
        };

        return (
            <div className="absolute inset-0 ${currentTheme.cardSolid} z-20 flex flex-col">
                <header className="${currentTheme.cardSolid} p-4 border-b ${currentTheme.border} flex items-center justify-between sticky top-0">
                    <h1 className="text-lg font-bold ${currentTheme.text}">Email Approval (Claude)</h1>
                    <button onClick={onClose} className="p-2 rounded-full hover:${currentTheme.buttonSecondary}">
                        <X className="w-5 h-5 ${currentTheme.textMuted}" />
                    </button>
                </header>
                <div className="flex-grow p-4 overflow-y-auto">
                    <Card title="Draft Email">
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium ${currentTheme.text}">To</label>
                                <input value={to} onChange={(e) => setTo(e.target.value)} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm p-2" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium ${currentTheme.text}">Subject</label>
                                <input value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm p-2" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium ${currentTheme.text}">Body</label>
                                <textarea rows={8} value={body} onChange={(e) => setBody(e.target.value)} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm p-2 whitespace-pre-wrap" />
                            </div>
                        </div>
                    </Card>
                </div>
                <div className="p-4 ${currentTheme.cardSolid} border-t ${currentTheme.border} flex gap-3">
                    <button onClick={handleReject} className="flex-1 bg-gray-200 ${currentTheme.text} py-3 rounded-lg font-semibold hover:bg-gray-300">Reject</button>
                    <button onClick={handleApprove} className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700">Approve & Send</button>
                </div>
            </div>
        );
    };

    // Simulated Webpage Component
    const SimulatedWebpage = ({ message, onClose }: { message: string, onClose: () => void }) => {
        const getWebpageContent = (message: string) => {
            if (message.includes("Michael got promoted")) {
                return {
                    title: "LinkedIn - Michael's Promotion",
                    url: "linkedin.com/posts/michael-promotion",
                    content: "Michael Johnson has been promoted to Lead Data Scientist at TechCorp. He shared his excitement about leading the data science team and working on cutting-edge AI projects. The post has received 150+ likes and 25+ comments from colleagues congratulating him on this achievement."
                };
            } else if (message.includes("Elon Musk")) {
                return {
                    title: "All-in Podcast - Optimus Discussion",
                    url: "allinpodcast.com/episodes/optimus-robots",
                    content: "In the latest All-in Podcast episode, Elon Musk discusses Tesla's Optimus humanoid robot, claiming it will be 'the best product ever' when fully developed. He explains the robot's potential applications in manufacturing, healthcare, and household assistance, with plans for mass production by 2025."
                };
            } else if (message.includes("Best Buy")) {
                return {
                    title: "Best Buy - Phone Deals",
                    url: "bestbuy.com/phone-deals",
                    content: "Best Buy is offering 10% off on all new smartphones for a limited time. This exclusive deal applies to the latest iPhone, Samsung Galaxy, and Google Pixel models. The promotion ends in 2 days, so don't miss out on these savings! Terms and conditions apply."
                };
            }
            return {
                title: "Related Article",
                url: "example.com/article",
                content: "This is a simulated webpage related to your feed item. In a real implementation, this would open the actual external link or app."
            };
        };

        const webpageData = getWebpageContent(message);

        return (
            <div className={`absolute inset-0 z-20 flex flex-col ${currentTheme.cardSolid}`}>
                <header className={`p-4 border-b flex items-center justify-between sticky top-0 shadow-sm ${currentTheme.cardSolid} ${currentTheme.border}`}>
                    <div className="flex items-center gap-3">
                        <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                        <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                        <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                    </div>
                    <div className="flex-1 mx-4">
                        <div className={`rounded-md px-3 py-1 text-sm ${currentTheme.buttonSecondary} ${currentTheme.textSecondary}`}>
                            {webpageData.url}
                        </div>
                    </div>
                    <button onClick={onClose} className={`p-2 rounded-full hover:opacity-80 transition-opacity ${currentTheme.buttonSecondary}`}>
                        <X className={`w-5 h-5 ${currentTheme.text}`} />
                    </button>
                </header>
                <div className={`flex-grow overflow-y-auto ${currentTheme.background}`}>
                    <div className="max-w-4xl mx-auto p-6">
                        <h1 className={`text-3xl font-bold mb-6 leading-tight ${currentTheme.text}`}>{webpageData.title}</h1>
                        <div className="space-y-6">
                            <div className="prose prose-lg max-w-none">
                                <p className={`text-lg leading-relaxed ${currentTheme.textSecondary}`}>{webpageData.content}</p>
                            </div>
                            <div className={`rounded-lg p-6 border ${currentTheme.cardSolid} ${currentTheme.border}`}>
                                <h3 className={`text-sm font-semibold mb-2 uppercase tracking-wide ${currentTheme.textMuted}`}>Simulated Webpage</h3>
                                <p className={`text-sm leading-relaxed ${currentTheme.textMuted}`}>
                                    This is a demo of how the feed item would open in a real browser or app.
                                    In production, this would navigate to the actual external link.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    // MyFeed Item for the dashboard feed with click-to-open and swipe-to-dismiss
    const WhatsUpItem = ({ icon: Icon, message, onOpenWebpage, onDismiss }: { icon: any, message: string, onOpenWebpage: (message: string) => void, onDismiss: () => void }) => {
        const [startX, setStartX] = useState(0);
        const [currentX, setCurrentX] = useState(0);
        const [isDragging, setIsDragging] = useState(false);
        const [isDismissed, setIsDismissed] = useState(false);
        const [isInteracting, setIsInteracting] = useState(false);

        const handleStart = (clientX: number) => {
            setStartX(clientX);
            setCurrentX(clientX);
            setIsDragging(false);
            setIsInteracting(true);
        };

        const handleMove = (clientX: number) => {
            if (!isInteracting) return;

            const deltaX = Math.abs(clientX - startX);
            if (deltaX > 10) { // If moved more than 10px, it's a drag
                setIsDragging(true);
            }
            setCurrentX(clientX);
        };

        const handleEnd = () => {
            if (!isInteracting) return;

            if (isDragging) {
                const deltaX = currentX - startX;
                const threshold = 100; // Minimum swipe distance

                if (Math.abs(deltaX) > threshold) {
                    // Swipe detected - dismiss the item
                    setIsDismissed(true);
                    setTimeout(() => {
                        onDismiss();
                    }, 300);
                }
            } else {
                // It was a click, not a drag
                onOpenWebpage(message);
            }

            setIsDragging(false);
            setIsInteracting(false);
            setCurrentX(0);
        };

        // Touch events
        const handleTouchStart = (e: React.TouchEvent) => {
            e.preventDefault();
            handleStart(e.touches[0].clientX);
        };

        const handleTouchMove = (e: React.TouchEvent) => {
            e.preventDefault();
            handleMove(e.touches[0].clientX);
        };

        const handleTouchEnd = (e: React.TouchEvent) => {
            e.preventDefault();
            handleEnd();
        };

        // Mouse events
        const handleMouseDown = (e: React.MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            handleStart(e.clientX);
            // Add global mouse event listeners for better drag experience
            document.addEventListener('mousemove', handleGlobalMouseMove);
            document.addEventListener('mouseup', handleGlobalMouseUp);
        };

        const handleGlobalMouseMove = (e: MouseEvent) => {
            e.preventDefault();
            handleMove(e.clientX);
        };

        const handleGlobalMouseUp = (e: MouseEvent) => {
            e.preventDefault();
            handleEnd();
            // Remove global listeners
            document.removeEventListener('mousemove', handleGlobalMouseMove);
            document.removeEventListener('mouseup', handleGlobalMouseUp);
        };


        // Cleanup effect to remove global event listeners
        useEffect(() => {
            return () => {
                document.removeEventListener('mousemove', handleGlobalMouseMove);
                document.removeEventListener('mouseup', handleGlobalMouseUp);
            };
        }, []);

        if (isDismissed) {
            return (
                <div className="p-3 opacity-0 transform translate-x-full transition-all duration-300">
                    <div className="flex items-start">
                        <div className="p-2 ${currentTheme.buttonSecondary} rounded-full mr-4">
                            <Icon className="w-5 h-5 ${currentTheme.textMuted}" />
                        </div>
                        <div className="flex-grow">
                            <p className="${currentTheme.text} text-sm leading-relaxed line-through">{message}</p>
                        </div>
                    </div>
                </div>
            );
        }

        const translateX = isDragging ? currentX - startX : 0;
        const opacity = isDragging ? Math.max(0.3, 1 - Math.abs(translateX) / 200) : 1;

        return (
            <div
                className={`p-3 hover:${currentTheme.surface} rounded-lg cursor-pointer transition-colors duration-200 relative overflow-hidden select-none`}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
                onMouseDown={handleMouseDown}
                style={{
                    transform: `translateX(${translateX}px)`,
                    opacity: opacity
                }}
            >
                <div className="flex items-start">
                    <div className={`p-2 ${currentTheme.buttonSecondary} rounded-full mr-4`}>
                        <Icon className={`w-5 h-5 ${currentTheme.text}`} />
                    </div>
                    <div className="flex-grow">
                        <p className={`${currentTheme.text} text-sm leading-relaxed`}>{message}</p>
                    </div>
                    <ArrowRight className={`w-5 h-5 ${currentTheme.textMuted} self-center ml-2`} />
                </div>

                {/* Swipe indicators */}
                {isDragging && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        {translateX > 50 && (
                            <div className="bg-red-400 text-white px-4 py-2 rounded-lg text-sm font-semibold">
                                Swipe to dismiss
                            </div>
                        )}
                        {translateX < -50 && (
                            <div className="bg-red-400 text-white px-4 py-2 rounded-lg text-sm font-semibold">
                                Swipe to dismiss
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    // Dashboard Page Component
    const Dashboard = ({ tasks, onReview, onSubmit }: { tasks: any[], onReview: (task: any) => void, onSubmit: (taskId: number) => void }) => {
        const reviewTasks = tasks.filter((t: any) => t.status === 'review');

        const handleReviewClick = (task: any) => {
            if (task.id === 1) { // Only show form for TD claim
                setCurrentScreen('td_form');
            }
            // Other tasks can have different review actions later
        };

        return (
            <div className="flex flex-col h-full">
                <div className="flex-grow overflow-y-auto space-y-6 pb-20">
                    {/* User Greeting with Status */}
                    {selectedPersona && (
                        <Card title="" className="border-l-4" style={{ borderLeftColor: selectedPersona === 'byakugan' ? '#3b82f6' : selectedPersona === 'sharingan' ? '#ef4444' : '#8b5cf6' }}>
                            <div className="flex items-center gap-3">
                                <div className={`bg-gradient-to-r ${currentTheme.primary} p-2 rounded-full`}>
                                    {React.createElement(personaConfig[selectedPersona].icon, {
                                        className: "w-5 h-5 text-white"
                                    })}
                                </div>
                                <div>
                                    <p className={`font-medium ${currentTheme.text}`}>
                                        Hey Arun Raj
                                    </p>
                                    <p className={`text-sm ${currentTheme.textSecondary}`}>
                                        I worked on three tasks and need your review
                                    </p>
                                </div>
                            </div>
                        </Card>
                    )}


                    {/* Tasks Section */}
                    {reviewTasks.length > 0 && (
                        <div>
                            <h3 className={`text-lg font-semibold mb-2 ${currentTheme.text}`}>
                                Tasks & Completions
                            </h3>
                            <div className={`rounded-xl border overflow-hidden ${currentTheme.cardSolid} ${currentTheme.border}`}>
                                {reviewTasks.map(task => (
                                    <TaskItem key={task.id} task={task} onReview={() => handleReviewClick(task)} onSubmit={onSubmit} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Updates Section */}
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${currentTheme.text}`}>My Feed</h3>
                        <div className={`${currentTheme.cardSolid} rounded-xl border ${currentTheme.border} divide-y ${currentTheme.border}`}>
                            {feedItems.map(item => (
                                <WhatsUpItem
                                    key={item.id}
                                    icon={item.icon}
                                    message={item.message}
                                    onOpenWebpage={handleOpenWebpage}
                                    onDismiss={() => handleDismissFeedItem(item.id)}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    // Integrations Page Component
    const IntegrationsPage = ({ onAddIntegrations, onOpenExternal }: { onAddIntegrations: () => void, onOpenExternal: (name: string) => void }) => (
         <div className="space-y-6">
            {/* Integrations */}
            <Card title="Integrations">
                <div className="space-y-3">
                    <div className={`flex items-center justify-between p-3 hover:${currentTheme.surface} rounded-lg transition-colors`}>
                        <div>
                            <p className={`font-medium ${currentTheme.text}`}>Gmail</p>
                            <p className={`text-xs ${currentTheme.textSecondary}`}>arun7569raj@gmail.com</p>
                        </div>
                        <span className="text-sm text-green-400 font-semibold">Active</span>
                    </div>
                    <div className={`flex items-center justify-between p-3 hover:${currentTheme.surface} rounded-lg transition-colors`}>
                        <div>
                            <p className={`font-medium ${currentTheme.text}`}>Outlook</p>
                            <p className={`text-xs ${currentTheme.textSecondary}`}>arunraj@live.com</p>
                        </div>
                        <span className="text-sm text-green-400 font-semibold">Active</span>
                    </div>
                    <div className={`flex items-center justify-between p-3 hover:${currentTheme.surface} rounded-lg transition-colors`}>
                        <p className={`font-medium ${currentTheme.text}`}>WhatsApp</p>
                        <span className="text-sm text-green-400 font-semibold">Active</span>
                    </div>
                    <div className={`flex items-center justify-between p-3 hover:${currentTheme.surface} rounded-lg transition-colors`}>
                        <p className={`font-medium ${currentTheme.text}`}>LinkedIn</p>
                        <span className="text-sm text-green-400 font-semibold">Active</span>
                    </div>
                </div>
            </Card>
            <button onClick={onAddIntegrations} className={`w-full py-3 rounded-lg font-semibold transition-opacity hover:opacity-90 ${currentTheme.button}`}>
                Add New Integration
            </button>

            {/* External Connections */}
            <Card title="External Connections">
                <div className="space-y-3">
                    <button onClick={() => onOpenExternal('Gemini')} className={`w-full text-left p-3 hover:${currentTheme.surface} rounded-lg flex items-center justify-between transition-colors`}>
                        <p className={`font-medium ${currentTheme.text}`}>Gemini</p>
                        <span className="text-sm text-green-400 font-semibold">Active</span>
                    </button>
                    <button onClick={() => onOpenExternal('Claude')} className={`w-full text-left p-3 hover:${currentTheme.surface} rounded-lg flex items-center justify-between transition-colors`}>
                        <p className={`font-medium ${currentTheme.text}`}>Claude</p>
                        <span className={`text-sm ${currentTheme.textSecondary} font-semibold`}>Inactive</span>
                    </button>
                </div>
            </Card>
        </div>
    );

    // Add New Integrations modal
    const AddIntegrationsModal = ({ onClose }: { onClose: () => void }) => {
        const topApps = [
            'Twitter', 'LinkedIn', 'Threads', 'Gmail', 'Outlook',
            'WhatsApp', 'Slack', 'Google Calendar', 'Notion', 'Trello'
        ];
        return (
            <div className={`absolute inset-0 z-20 flex flex-col ${currentTheme.cardSolid}`}>
                <header className={`p-4 border-b flex items-center justify-between sticky top-0 ${currentTheme.cardSolid} ${currentTheme.border}`}>
                    <h1 className={`text-lg font-bold ${currentTheme.text}`}>Add New Integrations</h1>
                    <button onClick={onClose} className={`p-2 rounded-full hover:${currentTheme.buttonSecondary} transition-colors`}>
                        <X className={`w-5 h-5 ${currentTheme.textMuted}`} />
                    </button>
                </header>
                <div className="flex-grow p-4 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-3">
                        {topApps.map(app => (
                            <button key={app} className="p-3 ${currentTheme.surface} hover:${currentTheme.buttonSecondary} rounded-lg border ${currentTheme.border} text-left font-medium">
                                {app}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        );
    };

    // External Connection configuration panel
    const ExternalConfigPanel = ({ name, onClose }: { name: string, onClose: () => void }) => {
        // Tools based on currently connected integrations
        const tools = [
            { id: 'gmail_send', label: 'Send Gmail message' },
            { id: 'outlook_send', label: 'Send Outlook message' },
            { id: 'linkedin_post', label: 'Post on LinkedIn' },
            { id: 'whatsapp_send', label: 'Send WhatsApp message' },
        ];
        const [access, setAccess] = useState(() => Object.fromEntries(tools.map(t => [t.id, 'needs'])) as Record<string, 'full' | 'needs' | 'none'>);
        const setLevel = (id: string, level: 'full' | 'needs' | 'none') => setAccess(prev => ({ ...prev, [id]: level }));

        const LevelKnob = ({ value, onChange }: { value: string, onChange: (level: string) => void }) => (
            <div className="inline-flex rounded-md border ${currentTheme.border} overflow-hidden">
                <button onClick={() => onChange('full')} className={`px-3 py-1 text-sm ${value==='full' ? 'bg-green-600 text-white' : '${currentTheme.cardSolid} ${currentTheme.text} hover:${currentTheme.surface}'}`}>Full access</button>
                <button onClick={() => onChange('needs')} className={`px-3 py-1 text-sm ${value==='needs' ? 'bg-yellow-500 text-white' : '${currentTheme.cardSolid} ${currentTheme.text} hover:${currentTheme.surface}'}`}>Needs approval</button>
                <button onClick={() => onChange('none')} className={`px-3 py-1 text-sm ${value==='none' ? 'bg-red-500 text-white' : '${currentTheme.cardSolid} ${currentTheme.text} hover:${currentTheme.surface}'}`}>No access</button>
            </div>
        );

        return (
            <div className="absolute inset-0 ${currentTheme.cardSolid} z-20 flex flex-col">
                <header className="${currentTheme.cardSolid} p-4 border-b ${currentTheme.border} flex items-center justify-between sticky top-0">
                    <h1 className="text-lg font-bold ${currentTheme.text}">Configure {name}</h1>
                    <button onClick={onClose} className="p-2 rounded-full hover:${currentTheme.buttonSecondary}">
                        <X className="w-5 h-5 ${currentTheme.textMuted}" />
                    </button>
                </header>
                <div className="flex-grow p-4 overflow-y-auto">
                    <Card title="Tool Access">
                        <div className="space-y-4">
                            {tools.map(tool => (
                                <div key={tool.id} className="flex items-center justify-between">
                                    <p className="text-sm font-medium ${currentTheme.text}">{tool.label}</p>
                                    <LevelKnob value={access[tool.id]} onChange={(lvl: string) => setLevel(tool.id, lvl as 'full' | 'needs' | 'none')} />
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>
            </div>
        );
    };

    // Done Page Component
    const DonePage = ({ tasks }: { tasks: any[] }) => {
        const doneTasks = tasks.filter((t: any) => t.status === 'done');
        return (
            <Card title="Completed Items">
                {doneTasks.length > 0 ? (
                    <div className="space-y-3">
                        {doneTasks.map((task: any) => (
                             <div key={task.id} className={`flex items-center p-3 rounded-lg ${currentTheme.surface}`}>
                                <div className={`p-2 rounded-full mr-4 ${currentTheme.buttonSecondary}`}>
                                    <task.icon className={`w-5 h-5 ${currentTheme.text}`} />
                                </div>
                                <p className={`font-medium ${currentTheme.text}`}>{task.title}</p>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className={`${currentTheme.textSecondary} text-center`}>No completed items yet.</p>
                )}
            </Card>
        );
    };

    // Settings Page Component
    const SettingsPage = () => {
         const [dynamicWakeup, setDynamicWakeup] = useState(true);
         return (
            <div className="space-y-4">
                <Card title="Personal Partner">
                    <div className="space-y-4">
                        <div>
                            <label className={`font-medium ${currentTheme.text}`}>Current Persona</label>
                            <p className={`text-sm ${currentTheme.textSecondary} mb-3`}>Choose your AI partner's personality</p>
                        </div>
                        <div className="grid gap-3">
                            {(Object.keys(personaConfig) as PersonaType[]).map((persona) => {
                                const config = personaConfig[persona];
                                const IconComponent = config.icon;
                                const isSelected = selectedPersona === persona;

                                return (
                                    <button
                                        key={persona}
                                        onClick={() => handlePersonaSelect(persona)}
                                        className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                                            isSelected
                                                ? `border-${currentTheme.accent} bg-gradient-to-r ${currentTheme.primary} text-white`
                                                : `${currentTheme.card} ${currentTheme.border} hover:border-gray-300`
                                        }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-full ${isSelected ? '${currentTheme.cardSolid}/20' : currentTheme.buttonSecondary}`}>
                                                <IconComponent className={`w-5 h-5 ${isSelected ? 'text-white' : currentTheme.textSecondary}`} />
                                            </div>
                                            <div className="text-left">
                                                <h3 className={`font-semibold ${isSelected ? 'text-white' : currentTheme.text}`}>
                                                    {config.name}
                                                </h3>
                                                <p className={`text-sm ${isSelected ? 'text-white/80' : currentTheme.textSecondary}`}>
                                                    {config.description}
                                                </p>
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </Card>
                <Card title="Preferences">
                    <div className="space-y-4">
                        <div>
                            <label className={`font-medium ${currentTheme.text}`}>Scan Frequency</label>
                            <p className={`text-sm ${currentTheme.textSecondary}`}>Every 2 hours</p>
                        </div>
                        <div className="flex items-center justify-between">
                            <div>
                                <label className={`font-medium ${currentTheme.text}`}>Dynamic Wakeup Logic</label>
                                <p className={`text-sm ${currentTheme.textSecondary}`}>Enable context-aware wakeups</p>
                            </div>
                            <button
                                type="button"
                                aria-pressed={dynamicWakeup}
                                onClick={() => setDynamicWakeup(v => !v)}
                                className={`flex items-center gap-2 px-3 py-2 rounded-md border transition-colors ${dynamicWakeup ? 'border-green-300 bg-green-50' : '${currentTheme.border} ${currentTheme.cardSolid} hover:${currentTheme.surface}'}`}
                            >
                                <span className={`inline-block w-2.5 h-2.5 rounded-full ${dynamicWakeup ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                                <span className={`text-sm font-medium ${currentTheme.text}`}>{dynamicWakeup ? 'On' : 'Off'}</span>
                            </button>
                        </div>
                    </div>
                </Card>
                <Card title="Account">
                    <div className="space-y-4">
                        <div>
                            <label className={`font-medium ${currentTheme.text}`}>Email</label>
                            <p className={`text-sm ${currentTheme.textSecondary}`}>arun7569raj@gmail.com</p>
                        </div>
                        <div>
                            <label className={`font-medium ${currentTheme.text}`}>Subscription</label>
                            <p className={`text-sm ${currentTheme.textSecondary}`}>Pro Plan</p>
                        </div>
                    </div>
                </Card>
                <button className="w-full bg-red-500 text-white py-3 rounded-lg font-semibold hover:bg-red-600 transition-colors">
                    Log Out
                </button>
            </div>
         );
    };

    // Main content renderer
    const renderContent = () => {
        switch (activePage) {
            case 'dashboard': return <Dashboard tasks={tasks} onReview={() => setCurrentScreen('td_form')} onSubmit={handleTaskSubmit} />;
            case 'integrations': return <IntegrationsPage onAddIntegrations={() => setShowAddIntegrations(true)} onOpenExternal={(name: string) => setSelectedExternal(name as 'Gemini' | 'Claude')} />;
            case 'done': return <DonePage tasks={tasks} />;
            case 'settings': return <SettingsPage />;
            default: return <Dashboard tasks={tasks} onReview={() => setCurrentScreen('td_form')} onSubmit={handleTaskSubmit} />;
        }
    };

    const currentTaskForForm = tasks.find(t => t.id === 1 && t.status === 'review');

    return (
        <div className={`min-h-screen ${currentTheme.gradient} flex justify-center items-center p-4 font-sans`}>
            {/* Mobile App Container */}
            <div className={`relative w-full max-w-sm h-[85vh] max-h-[900px] shadow-2xl rounded-3xl overflow-hidden flex flex-col min-h-0 ${currentTheme.cardSolid}`}>
                {/* Persona Onboarding Screen */}
                {showOnboarding && <PersonaOnboarding />}

                {currentScreen === 'td_form' && currentTaskForForm && (
                     <TdClaimForm task={currentTaskForForm} onSubmit={handleTaskSubmit} />
                )}
                {showAddIntegrations && (
                    <AddIntegrationsModal onClose={() => setShowAddIntegrations(false)} />
                )}
                {selectedExternal && (
                    <ExternalConfigPanel name={selectedExternal} onClose={() => setSelectedExternal(null)} />
                )}
                {showClaudeEmailPanel && (
                    <EmailApprovalPanel onClose={() => setShowClaudeEmailPanel(false)} />
                )}
                {showWebpage && (
                    <SimulatedWebpage
                        message={webpageMessage}
                        onClose={() => setShowWebpage(false)}
                    />
                )}
                <div className={`flex flex-col flex-grow min-h-0 ${currentScreen !== 'main' ? 'hidden' : ''}`}>
                    <Header userEmail="arun7569raj@gmail.com" />

                    {/* Expandable Text Input Section */}
                    {showTextInput && (
                        <div className="mx-4 mt-2 animate-in slide-in-from-top duration-300">
                            <div className={`rounded-xl shadow-sm border backdrop-blur-sm ${currentTheme.cardSolid} ${currentTheme.border}`}>
                                <div className="p-4 space-y-4">
                                    <div className="relative">
                                        <textarea
                                            className={`w-full py-3 pl-4 pr-20 border rounded-lg focus:outline-none focus:ring-2 resize-none transition-all ${currentTheme.buttonSecondary} ${currentTheme.border} ${currentTheme.text}`}
                                            placeholder="Ask anything or delegate task..."
                                            rows={3}
                                        />
                                        <div className="absolute bottom-2 right-2 flex gap-2">
                                            <button
                                                className={`text-white p-2 rounded-full hover:opacity-90 transition-opacity shadow-md ${currentTheme.button}`}
                                                title="Voice input"
                                            >
                                                <Mic className="w-4 h-4" />
                                            </button>
                                            <button
                                                className={`text-white p-2 rounded-full hover:opacity-90 transition-opacity shadow-md ${currentTheme.button}`}
                                                title="Send message"
                                            >
                                                <Send className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                    <div className={`flex items-center justify-between text-sm ${currentTheme.textSecondary}`}>
                                        <span>💡 Tip: Click the logo again to minimize</span>
                                        <button
                                            onClick={() => setShowTextInput(false)}
                                            className={`hover:opacity-70 transition-opacity ${currentTheme.textMuted}`}
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <main className={`flex-grow min-h-0 overflow-y-auto p-4 ${currentTheme.background}`}>
                        {renderContent()}
                    </main>
                    <BottomNav activePage={activePage} setActivePage={setActivePage} />
                </div>
            </div>
        </div>
    );
};

export default App;
