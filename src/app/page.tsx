'use client'

import { useState } from 'react'
import { EventList } from '@/components/event-list'
import { EventForm } from '@/components/event-form'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Plus, List } from 'lucide-react'

export default function Home() {
  const [activeTab, setActiveTab] = useState('events')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                Exhibit Board
              </h1>
              <span className="ml-3 text-sm text-gray-500">
                展示・グループ展の開催情報掲示板
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="events" className="flex items-center gap-2">
              <List className="w-4 h-4" />
              展示一覧
            </TabsTrigger>
            <TabsTrigger value="submit" className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              新規登録
            </TabsTrigger>
          </TabsList>

          <TabsContent value="events" className="space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold text-gray-900">
                展示情報一覧
              </h2>
              <p className="text-gray-600">
                個展・グループ展の開催情報を地域や期間で絞り込んで表示できます
              </p>
            </div>
            <EventList />
          </TabsContent>

          <TabsContent value="submit" className="space-y-6">
            <div className="text-center space-y-2 mb-8">
              <h2 className="text-3xl font-bold text-gray-900">
                展示情報登録
              </h2>
              <p className="text-gray-600">
                あなたの展示情報を登録して、多くの人に知ってもらいましょう
              </p>
            </div>
            <EventForm 
              onSuccess={() => {
                // Switch to events tab after successful submission
                setActiveTab('events')
              }}
            />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-600">
            <p>
              © 2025 Exhibit Board. 
              展示情報は告知元のSNS投稿が一次情報です。詳細は各告知をご確認ください。
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
