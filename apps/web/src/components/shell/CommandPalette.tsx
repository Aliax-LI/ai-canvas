import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { allNavItems } from "@/lib/navigation";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="搜索页面或操作…" />
      <CommandList>
        <CommandEmpty>未找到匹配项</CommandEmpty>
        <CommandGroup heading="导航">
          {allNavItems.map((item) => (
            <CommandItem
              key={item.href}
              value={`${item.title} ${item.description ?? ""}`}
              onSelect={() => {
                navigate(item.href);
                setOpen(false);
              }}
            >
              <item.icon className="size-4" strokeWidth={1.5} />
              <span>{item.title}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
