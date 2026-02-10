import ElephantIcon from "./ElephantIcon";

export default function Header() {
  return (
    <header className="bg-white/10 backdrop-blur-md text-white px-6 py-3.5 border-b border-white/20">
      <div className="max-w-4xl mx-auto flex items-center gap-3">
        <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center text-white shadow-lg">
          <ElephantIcon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight leading-tight text-white">
            TanyaAka ITB
          </h1>
          <p className="text-[11px] text-white/70 leading-tight font-medium">
            Asisten Akademik Cerdas
          </p>
        </div>
      </div>
    </header>
  );
}
