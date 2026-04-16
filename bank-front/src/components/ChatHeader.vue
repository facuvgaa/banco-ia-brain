<template>
  <header class="p-4 border-b border-emerald-500/20 bg-zinc-900/50 backdrop-blur-md flex justify-between items-center sticky top-0 z-10">
    <div class="flex items-center gap-3">
      <div class="relative">
        <div class="w-3 h-3 bg-emerald-500 rounded-full"></div>
        <div class="w-3 h-3 bg-emerald-500 rounded-full animate-ping absolute top-0"></div>
      </div>
      <h1 class="text-xl font-black text-emerald-400 tracking-tighter uppercase">
        Moustro <span class="text-white">Bank_IA</span>
      </h1>
    </div>
    <div class="hidden md:block">
      <span class="px-3 py-1 rounded-full border border-zinc-700 text-[10px] font-mono text-zinc-500 bg-zinc-800">
        NODES: ACTIVE | KAFKA: OK
      </span>
    </div>
  </header>
</template>
