import { Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import './App.css';

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default App;
