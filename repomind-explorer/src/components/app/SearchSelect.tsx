import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export function SearchSelect<T extends string>({
  value,
  options,
  onChange,
  format = (v) => v,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  className,
  id,
}: {
  value: T | null;
  options: T[];
  onChange: (v: T) => void;
  format?: (v: T) => string;
  placeholder?: string;
  searchPlaceholder?: string;
  className?: string;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          id={id}
          type="button"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "flex h-10 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 text-left text-sm transition-colors hover:bg-accent/40",
            className,
          )}
        >
          <span className="truncate">{value ? format(value) : <span className="text-muted-foreground">{placeholder}</span>}</span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[320px] p-0" align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList className="max-h-80">
            <CommandEmpty>No matches.</CommandEmpty>
            <CommandGroup>
              {options.map((o) => (
                <CommandItem
                  key={o}
                  value={`${format(o)} ${o}`}
                  onSelect={() => {
                    onChange(o);
                    setOpen(false);
                  }}
                  className="text-[13px]"
                >
                  <Check className={cn("h-3.5 w-3.5", value === o ? "opacity-100" : "opacity-0")} />
                  <span className="truncate">{format(o)}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
