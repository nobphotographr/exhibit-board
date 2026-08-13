'use client'

import { useState } from 'react'
import { EventList } from '@/components/event-list'
import { EventForm } from '@/components/event-form'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Plus, List } from 'lucide-react'

export default function Home() {
  const [activeTab, setActiveTab] = useState('events')

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 sm:px-8">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-8 gap-2">
            <h1 className="text-2xl font-semibold text-foreground">
              Exhibit Board
            </h1>
            <span className="text-sm text-muted-foreground">
              全国の写真展・写真祭情報
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 sm:px-8 py-12 sm:py-16">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-10 sm:space-y-12">
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="events" className="flex items-center gap-2">
              <List className="w-4 h-4" />
              展示一覧
            </TabsTrigger>
            <TabsTrigger value="submit" className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              情報を投稿
            </TabsTrigger>
          </TabsList>

          <TabsContent value="events" className="space-y-8">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold text-foreground">
                写真展を探す
              </h2>
              <p className="text-muted-foreground">
                キーワード・会期・地域・展示規模から開催情報を絞り込めます
              </p>
            </div>
            <EventList />
          </TabsContent>

          <TabsContent value="submit" className="space-y-8">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold text-foreground">
                展示情報登録
              </h2>
              <p className="text-muted-foreground">
                写真展の情報をお寄せください。内容を確認後に掲載します
              </p>
            </div>
            <EventForm />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-24">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 py-8">
          <div className="text-sm text-muted-foreground space-y-2">
            <p>
              展示情報は会場・主催者の公式サイトまたは告知元のSNS投稿をもとに掲載しています。詳細は各告知をご確認ください。
            </p>
            <p>
              修正があれば
              <a
                href="https://x.com/novy_jp"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-4 decoration-border hover:decoration-foreground mx-1"
              >
                @novy_jp
              </a>
              までご連絡ください。
            </p>
            <p>
              当サイトでは利用状況の把握と改善のため Google Analytics を使用し、ページ閲覧やリンク操作などの情報を収集しています。詳しくは
              <a
                href="https://policies.google.com/technologies/partner-sites?hl=ja"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-4 decoration-border hover:decoration-foreground mx-1"
              >
                Google によるデータ利用について
              </a>
              をご確認ください。
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
