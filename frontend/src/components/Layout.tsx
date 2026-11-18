import clsx from 'clsx';
import { NavLink, Outlet } from 'react-router-dom';

const link = ({ isActive }: { isActive: boolean }) =>
  clsx('rounded-md px-3 py-2 text-sm font-semibold', isActive ? 'bg-white/15 text-white' : 'text-white/75 hover:text-white');

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-asphalt">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <span className="flex items-center gap-2 font-extrabold text-white">
            <img src="/favicon.svg" alt="" width={24} height={24} />
            FaceAttend
          </span>
          <nav aria-label="Main" className="ml-auto flex gap-1">
            <NavLink to="/" end className={link}>Kiosk</NavLink>
            <NavLink to="/technicians" className={link}>Technicians</NavLink>
            <NavLink to="/attendance" className={link}>Attendance</NavLink>
          </nav>
        </div>
        {/* Reflective road-marking stripe */}
        <div className="h-1 bg-[repeating-linear-gradient(90deg,#F2C200_0_32px,transparent_32px_56px)]" aria-hidden />
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
