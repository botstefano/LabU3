import Sidebar from "./Sidebar";
import Navbar from "./Navbar";

export default function AppLayout({ title, children }) {
  return (
    <div className="flex min-h-screen bg-paper-50">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Navbar title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
