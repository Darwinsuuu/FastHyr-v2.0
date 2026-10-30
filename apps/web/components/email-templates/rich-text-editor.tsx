"use client";

import {
  BracketsSquareIcon,
  CaretDownIcon,
  LinkBreakIcon,
  LinkSimpleIcon,
  ListBulletsIcon,
  TextBIcon,
  TextItalicIcon,
} from "@phosphor-icons/react";
import { mergeAttributes, Node } from "@tiptap/core";
import { EditorContent, useEditor, useEditorState } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  type FormEvent,
  forwardRef,
  type ReactNode,
  useEffect,
  useId,
  useImperativeHandle,
  useState,
} from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { cn } from "@/lib/cn";
import { linkHref, withoutParameterChips, withParameterChips } from "@/lib/email-templates";
import { t } from "@/lib/i18n";

/** A `[Candidate.firstname]` chip: one piece the cursor steps over, stored as plain text. */
const Parameter = Node.create({
  name: "parameter",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,
  addAttributes() {
    return {
      name: {
        default: "",
        parseHTML: (element) => element.getAttribute("data-parameter") ?? "",
        renderHTML: (attributes) => ({ "data-parameter": attributes.name as string }),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span[data-parameter]" }];
  },
  renderHTML({ node, HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(HTMLAttributes, { class: "fh-parameter" }),
      `[${node.attrs.name as string}]`,
    ];
  },
  renderText({ node }) {
    return `[${node.attrs.name as string}]`;
  },
});

export interface RichTextEditorHandle {
  insertParameter: (name: string) => void;
}

export interface RichTextEditorProps {
  /** The stored HTML (plain `[Parameter]` text); read again when `contentKey` changes. */
  value: string;
  contentKey: string;
  /** The HTML to store, chips back to plain text. */
  onChange: (html: string) => void;
  parameters: string[];
  editable: boolean;
  labelledBy: string;
  describedBy?: string;
  invalid?: boolean;
  /** Shown under the message inside the frame, e.g. the locked review line. */
  footer?: ReactNode;
}

/** The message editor (frame EditEmailTemplate): bold, italic, link, bullets and parameter
 * chips, nothing else, so what's typed is what the email allow-list keeps. */
export const RichTextEditor = forwardRef<RichTextEditorHandle, RichTextEditorProps>(
  function RichTextEditor(
    { value, contentKey, onChange, parameters, editable, labelledBy, describedBy, invalid, footer },
    ref,
  ) {
    const editor = useEditor({
      immediatelyRender: false,
      extensions: [
        StarterKit.configure({
          blockquote: false,
          code: false,
          codeBlock: false,
          heading: false,
          horizontalRule: false,
          orderedList: false,
          strike: false,
          underline: false,
          link: {
            openOnClick: false,
            autolink: false,
            protocols: ["mailto"],
            HTMLAttributes: { rel: null, target: null },
          },
        }),
        Parameter,
      ],
      content: withParameterChips(value),
      editable,
      editorProps: {
        attributes: {
          role: "textbox",
          "aria-multiline": "true",
          "aria-labelledby": labelledBy,
          ...(describedBy ? { "aria-describedby": describedBy } : {}),
          class: "fh-message min-h-[280px] px-4 py-4 outline-none md:min-h-[320px] md:px-[18px]",
        },
      },
      onUpdate: ({ editor: current }) => onChange(withoutParameterChips(current.getHTML())),
    });

    // A new version to show (restore, reset, history): replace the content without an update.
    useEffect(() => {
      if (!editor) return;
      editor.commands.setContent(withParameterChips(value), { emitUpdate: false });
      // eslint-disable-next-line react-hooks/exhaustive-deps -- only when the version changes
    }, [editor, contentKey]);

    useEffect(() => {
      editor?.setEditable(editable, false);
    }, [editor, editable]);

    useEffect(() => {
      editor?.setOptions({
        editorProps: {
          attributes: {
            ...(editor.options.editorProps.attributes as Record<string, string>),
            "aria-invalid": invalid ? "true" : "false",
            "aria-readonly": editable ? "false" : "true",
          },
        },
      });
    }, [editor, invalid, editable]);

    useImperativeHandle(
      ref,
      () => ({
        insertParameter: (name: string) => {
          if (!editor || !editable) return;
          editor
            .chain()
            .focus()
            .insertContent([
              { type: "parameter", attrs: { name } },
              { type: "text", text: " " },
            ])
            .run();
        },
      }),
      [editor, editable],
    );

    const active = useEditorState({
      editor,
      selector: ({ editor: current }) => ({
        bold: current?.isActive("bold") ?? false,
        italic: current?.isActive("italic") ?? false,
        link: current?.isActive("link") ?? false,
        list: current?.isActive("bulletList") ?? false,
      }),
    });

    const [linkOpen, setLinkOpen] = useState(false);
    const [linkValue, setLinkValue] = useState("");
    const [linkError, setLinkError] = useState(false);
    const linkId = useId();

    function openLink() {
      if (!editor) return;
      setLinkValue((editor.getAttributes("link").href as string | undefined) ?? "");
      setLinkError(false);
      setLinkOpen(true);
    }

    function applyLink(event: FormEvent) {
      event.preventDefault();
      if (!editor) return;
      const href = linkHref(linkValue);
      if (!href) {
        setLinkError(true);
        return;
      }
      const chain = editor.chain().focus();
      if (editor.state.selection.empty && !editor.isActive("link")) {
        chain
          .insertContent({
            type: "text",
            text: linkValue.trim(),
            marks: [{ type: "link", attrs: { href } }],
          })
          .run();
      } else {
        chain.extendMarkRange("link").setLink({ href }).run();
      }
      setLinkOpen(false);
    }

    const disabled = !editor || !editable;

    return (
      <div
        className={cn(
          "flex flex-col rounded-sm border bg-surface-raised",
          invalid ? "border-signal-gap" : "border-line-strong",
          !editable && "bg-surface",
        )}
      >
        <div
          role="toolbar"
          aria-label={t("emailTemplates.editor.toolbar")}
          className="flex flex-wrap items-center gap-0.5 rounded-t-sm border-b border-line bg-surface px-2 py-1.5"
        >
          <ToolButton
            label={t("emailTemplates.editor.bold")}
            pressed={active?.bold}
            disabled={disabled}
            onClick={() => editor?.chain().focus().toggleBold().run()}
          >
            <TextBIcon weight="bold" />
          </ToolButton>
          <ToolButton
            label={t("emailTemplates.editor.italic")}
            pressed={active?.italic}
            disabled={disabled}
            onClick={() => editor?.chain().focus().toggleItalic().run()}
          >
            <TextItalicIcon />
          </ToolButton>
          <ToolButton
            label={t("emailTemplates.editor.link")}
            pressed={active?.link || linkOpen}
            disabled={disabled}
            onClick={openLink}
          >
            <LinkSimpleIcon />
          </ToolButton>
          <ToolButton
            label={t("emailTemplates.editor.bulletList")}
            pressed={active?.list}
            disabled={disabled}
            onClick={() => editor?.chain().focus().toggleBulletList().run()}
          >
            <ListBulletsIcon />
          </ToolButton>
          <span aria-hidden="true" className="mx-1.5 h-5 w-px bg-line" />
          <Menu
            title={t("emailTemplates.editor.insertParameter")}
            align="start"
            items={parameters.map((name) => ({
              label: `[${name}]`,
              onSelect: () => {
                editor
                  ?.chain()
                  .focus()
                  .insertContent([
                    { type: "parameter", attrs: { name } },
                    { type: "text", text: " " },
                  ])
                  .run();
              },
            }))}
            trigger={
              <button
                type="button"
                disabled={disabled}
                className="inline-flex h-11 items-center gap-1.5 rounded-[8px] border border-line bg-surface-raised px-2.5 text-[13px] font-semibold text-evergreen disabled:opacity-45 md:h-8"
              >
                <BracketsSquareIcon aria-hidden="true" className="size-4" />
                {t("emailTemplates.editor.insertParameter")}
                <CaretDownIcon aria-hidden="true" className="size-3.5" />
              </button>
            }
          />
        </div>

        {linkOpen && (
          <form
            onSubmit={applyLink}
            className="flex flex-col gap-2 border-b border-line px-2.5 py-2 sm:flex-row sm:items-center"
          >
            <label htmlFor={linkId} className="text-[13px] font-semibold whitespace-nowrap">
              {t("emailTemplates.editor.linkTo")}
            </label>
            <Input
              id={linkId}
              type="text"
              inputMode="url"
              autoFocus
              value={linkValue}
              placeholder="https://"
              aria-invalid={linkError || undefined}
              aria-describedby={linkError ? `${linkId}-error` : undefined}
              onChange={(event) => {
                setLinkValue(event.target.value);
                setLinkError(false);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") setLinkOpen(false);
              }}
              className="h-11 sm:h-9 sm:flex-1"
            />
            <div className="flex gap-2">
              <Button type="submit" size="sm">
                {t("emailTemplates.editor.addLink")}
              </Button>
              {active?.link && (
                <Button
                  type="button"
                  size="sm"
                  variant="quiet"
                  icon={<LinkBreakIcon aria-hidden="true" />}
                  onClick={() => {
                    editor?.chain().focus().extendMarkRange("link").unsetLink().run();
                    setLinkOpen(false);
                  }}
                >
                  {t("emailTemplates.editor.removeLink")}
                </Button>
              )}
              <Button type="button" size="sm" variant="quiet" onClick={() => setLinkOpen(false)}>
                {t("emailTemplates.editor.linkCancel")}
              </Button>
            </div>
            {linkError && (
              <p id={`${linkId}-error`} className="text-[13px] text-signal-gap sm:basis-full">
                {t("emailTemplates.editor.linkInvalid")}
              </p>
            )}
          </form>
        )}

        <EditorContent editor={editor} className="flex-1" />
        {footer}
      </div>
    );
  },
);

function ToolButton({
  label,
  pressed,
  disabled,
  onClick,
  children,
}: {
  label: string;
  pressed?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={pressed ?? false}
      disabled={disabled}
      // Keep the editor's selection: the click shouldn't move focus out of the message first.
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
      className={cn(
        "flex size-11 items-center justify-center rounded-[8px] text-ink transition-colors md:size-9",
        "hover:bg-surface-sunk disabled:opacity-45 disabled:hover:bg-transparent [&>svg]:size-[18px]",
        pressed && "bg-evergreen-soft text-evergreen hover:bg-evergreen-soft",
      )}
    >
      {children}
    </button>
  );
}
