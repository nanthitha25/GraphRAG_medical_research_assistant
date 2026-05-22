import { ChatInterface } from '../../components/Chat/ChatInterface';

export default function Home() {
  return (
    <main className="h-screen w-full flex flex-col bg-slate-50">
      <ChatInterface />
    </main>
  );
}
